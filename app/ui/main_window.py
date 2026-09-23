from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, QUrl, Signal, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QStackedWidget, QVBoxLayout, QWidget)

from app.audio.media import MediaError, SUPPORTED_EXTENSIONS, format_duration, get_duration
from app.branding import CONTACT_EMAIL, CREATOR_NAME, SUPPORT_URL
from app.config.settings import APP_DATA_DIR, SettingsStore
from app.hardware.gpu import detect_gpu_runtime
from app.hardware.profiles import resolve_profile
from app.jobs.runner import JobCancelled, JobResult, Progress, TranscriptionJob
from app.transcription.model_manager import ModelManager
from app.ui.components.cards import GlassButton, GlassDropdown, GlassProgress
from app.ui.i18n import Translator
from app.ui.model_download import ModelDownloadConfirmationDialog, ModelDownloadProgressDialog, ModelDownloadWorker
from app.ui.dashboard import CommandSurface, ThemeToggleButton, WaveformIcon, WaveformWidget, WaveformWorker
from app.ui.platform.windows_surface import ensure_opaque_surface, prepare_opaque_window
from app.ui.theme.manager import ThemeManager


class JobWorker(QObject):
    progress = Signal(object); warning = Signal(str); finished = Signal(object); cancelled = Signal(); failed = Signal(str)
    def __init__(self, job: TranscriptionJob, unknown_error: str) -> None:
        super().__init__(); self.job, self.unknown_error = job, unknown_error
    def run(self) -> None:
        try: self.finished.emit(self.job.run())
        except JobCancelled: self.cancelled.emit()
        except Exception as error:
            logging.getLogger("transcripta").exception("Job failed"); self.failed.emit(str(error) or self.unknown_error)


class MainWindow(QMainWindow):
    def __init__(self, settings_store: SettingsStore) -> None:
        super().__init__(); self.settings_store, self.settings = settings_store, settings_store.load()
        # The simplified product has one automatic deliverable.  Normalise old
        # multi-format preferences when the application opens, before a job can
        # read them.
        if self.settings.general.theme == "system":
            self.settings.general.theme = "dark" if QApplication.instance().styleHints().colorScheme() == Qt.ColorScheme.Dark else "light"
        self.settings_store.save(self.settings)
        self.translator = Translator(self.settings.general.language); self.source: Path | None = None; self.duration = 0.0
        self.job: TranscriptionJob | None = None; self.thread: QThread | None = None; self.worker: JobWorker | None = None; self.last_result: JobResult | None = None
        self.model_manager = ModelManager(APP_DATA_DIR / "models"); self.download_thread: QThread | None = None; self.download_worker: ModelDownloadWorker | None = None; self.download_dialog: ModelDownloadProgressDialog | None = None
        self._pending_profile = None; self._pending_start = False; self._retry_download_label: str | None = None
        self._last_progress: Progress | None = None; self._eta_seconds: float | None = None; self._active_profile = None
        self.waveform_thread: QThread | None = None; self.waveform_worker: WaveformWorker | None = None
        self._surface_backend = "solid-native-surface"; self._surface_applied = False
        prepare_opaque_window(self); self.setMinimumSize(760, 560); self.resize(960, 680); self.setAcceptDrops(True); ThemeManager.apply(QApplication.instance(), self.settings.general.theme)
        style_hints = QApplication.instance().styleHints()
        if hasattr(style_hints, "colorSchemeChanged"): style_hints.colorSchemeChanged.connect(self._on_system_theme_changed)
        self._build_ui(); self._show_device()
    def t(self, key: str, **values: object) -> str: return self.translator(key, **values)
    def _on_system_theme_changed(self, _scheme) -> None:
        if self.settings.general.theme == "system": ThemeManager.apply(QApplication.instance(), "system")
    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._surface_applied:
            self._surface_backend = ensure_opaque_surface(self); self._surface_applied = True
    def _build_ui(self) -> None:
        self.setWindowTitle(self.t("window_title")); root = QWidget(); root.setObjectName("dashboardRoot")
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root); root_layout.setContentsMargins(24, 22, 24, 18)
        self.console = CommandSurface(); console_layout = QVBoxLayout(self.console); console_layout.setContentsMargins(28, 22, 28, 16); console_layout.setSpacing(12); root_layout.addWidget(self.console)
        header = QHBoxLayout()
        title = QLabel(self.t("module_name")); title.setObjectName("wordmark")
        subtitle = QLabel(self.t("tagline")); subtitle.setObjectName("subtitle")
        header.addWidget(title); header.addSpacing(18); header.addWidget(subtitle); header.addStretch()
        self.theme_button = ThemeToggleButton(self.settings.general.theme, self.t("switch_theme"))
        self.theme_button.clicked.connect(self._toggle_theme)
        self.ru_button = GlassButton("RU"); self.en_button = GlassButton("EN")
        self.ru_button.setAccessibleName("Русский"); self.en_button.setAccessibleName("English")
        self.ru_button.clicked.connect(lambda: self._set_language("ru")); self.en_button.clicked.connect(lambda: self._set_language("en"))
        header.addWidget(self.theme_button); header.addWidget(self.ru_button); header.addWidget(self.en_button); console_layout.addLayout(header)
        workspace = QWidget(); workspace.setObjectName("workspacePanel"); self.drop_area = self.console
        work_layout = QVBoxLayout(workspace); work_layout.setContentsMargins(0, 0, 0, 0); work_layout.setSpacing(12)
        content_column = QWidget(); content_column.setObjectName("contentColumn"); content_column.setMaximumWidth(820)
        content_layout = QVBoxLayout(content_column); content_layout.setContentsMargins(0, 0, 0, 0); content_layout.addWidget(workspace)
        console_layout.addWidget(content_column, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.workspace_stack = QStackedWidget(); self.workspace_stack.setObjectName("workspaceStack"); work_layout.addWidget(self.workspace_stack)

        self.empty_page = QWidget(); self.empty_page.setObjectName("emptyPage"); empty_layout = QVBoxLayout(self.empty_page); empty_layout.setContentsMargins(0, 0, 0, 0); empty_layout.setSpacing(14)
        empty_layout.addStretch(3); self.empty_icon = WaveformIcon(); empty_layout.addWidget(self.empty_icon, alignment=Qt.AlignmentFlag.AlignCenter)
        self.empty_hint = QLabel(self.t("drop_title")); self.empty_hint.setObjectName("emptyHint"); self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter); empty_layout.addWidget(self.empty_hint)
        self.empty_subhint = QLabel(self.t("drop_or_choose")); self.empty_subhint.setObjectName("emptySubhint"); self.empty_subhint.setAlignment(Qt.AlignmentFlag.AlignCenter); empty_layout.addWidget(self.empty_subhint)
        self.choose_button = GlassButton(self.t("upload_file")); self.choose_button.setObjectName("chooseSource"); self.choose_button.clicked.connect(self.select_file); empty_layout.addWidget(self.choose_button, alignment=Qt.AlignmentFlag.AlignCenter); empty_layout.addStretch(4)
        self.workspace_stack.addWidget(self.empty_page)

        self.source_page = QWidget(); self.source_page.setObjectName("sourcePage"); source_layout = QVBoxLayout(self.source_page); source_layout.setContentsMargins(0, 0, 0, 0); source_layout.setSpacing(14); self.workspace_stack.addWidget(self.source_page)
        file_header = QWidget(); file_header_layout = QHBoxLayout(file_header); file_header_layout.setContentsMargins(0, 0, 0, 0); self.file_label = QLabel(self.t("workspace_empty_title")); self.file_label.setObjectName("fileName")
        self.duration_label, self.size_label, self.file_state = QLabel(""), QLabel(""), QLabel(self.t("workspace_empty_detail")); self.duration_label.setObjectName("fileMeta"); self.size_label.setObjectName("fileMeta"); self.file_state.setObjectName("fileMeta")
        self.clear_source_button = GlassButton("×"); self.clear_source_button.setObjectName("clearSource"); self.clear_source_button.setFixedWidth(34); self.clear_source_button.setVisible(False); self.clear_source_button.clicked.connect(self._clear_source)
        file_header_layout.addWidget(self.file_label, 1); file_header_layout.addWidget(self.duration_label); file_header_layout.addWidget(self.size_label); file_header_layout.addWidget(self.clear_source_button); source_layout.addWidget(file_header)
        self.waveform = WaveformWidget(); source_layout.addWidget(self.waveform)
        selectors = QHBoxLayout(); selectors.setSpacing(0); selectors.addStretch()
        selector_group = QWidget(); selector_group.setObjectName("selectorGroup"); selector_group_layout = QHBoxLayout(selector_group); selector_group_layout.setContentsMargins(0, 0, 0, 0); selector_group_layout.setSpacing(12)
        self.mode_combo = GlassDropdown()
        for label, value in ((self.t("eco"), "eco"), (self.t("balanced"), "balanced"), (self.t("maximum_speed"), "maximum_speed")):
            self.mode_combo.addItem(label, value)
        self.mode_combo.setCurrentIndex(max(0, self.mode_combo.findData(self.settings.recognition.performance_profile)))
        self.mode_combo.currentIndexChanged.connect(self._set_performance_profile)
        self.language_combo = GlassDropdown(); self.language_combo.addItem(self.t("auto"), "auto"); self.language_combo.addItem(self.t("russian"), "ru"); self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(self.settings.recognition.language))); self.language_combo.currentIndexChanged.connect(self._set_recognition_language)
        for title_text, value in ((self.t("selector_mode"), self.mode_combo), (self.t("selector_recording_language"), self.language_combo)):
            selector = QWidget(); selector.setFixedWidth(180); selector_layout = QVBoxLayout(selector); selector_layout.setContentsMargins(0, 0, 0, 0); selector_layout.setSpacing(5); label = QLabel(title_text); label.setObjectName("controlLabel"); selector_layout.addWidget(label); selector_layout.addWidget(value); selector_group_layout.addWidget(selector)
        selectors.addWidget(selector_group); selectors.addStretch()
        source_layout.addLayout(selectors)
        self.action_layout = QHBoxLayout(); self.action_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.start_button = GlassButton(self.t("start") + "  →"); self.start_button.setObjectName("primary"); self.start_button.clicked.connect(self.start); self.action_layout.addWidget(self.start_button); source_layout.addLayout(self.action_layout)

        self.processing_page = QWidget(); self.processing_page.setObjectName("processingPage"); processing_layout = QVBoxLayout(self.processing_page); processing_layout.setContentsMargins(0, 0, 0, 0); processing_layout.setSpacing(0); processing_layout.addStretch()
        self.processing_content = QWidget(); self.processing_content.setObjectName("processingContent"); self.processing_content.setMaximumWidth(620); processing_content_layout = QVBoxLayout(self.processing_content); processing_content_layout.setContentsMargins(0, 0, 0, 0); processing_content_layout.setSpacing(14)
        self.processing_title = QLabel(self.t("processing_title")); self.processing_title.setObjectName("processingTitle"); self.processing_title.setAlignment(Qt.AlignmentFlag.AlignCenter); processing_content_layout.addWidget(self.processing_title)
        self.progress_percent = QLabel(); self.progress_percent.setObjectName("progressPercent"); self.progress_percent.setAlignment(Qt.AlignmentFlag.AlignCenter); processing_content_layout.addWidget(self.progress_percent)
        self.progress = GlassProgress(); self.progress.setRange(0, 100); self.progress.setValue(0); self.progress.setTextVisible(False); self.progress.setFixedHeight(14); processing_content_layout.addWidget(self.progress)
        self.progress_details = QLabel(); self.progress_details.setObjectName("progressDetails"); self.progress_details.setAlignment(Qt.AlignmentFlag.AlignCenter); processing_content_layout.addWidget(self.progress_details)
        self.status = QLabel(); self.status.setObjectName("workspaceStatus"); self.status.setWordWrap(True); self.status.setAlignment(Qt.AlignmentFlag.AlignCenter); processing_content_layout.addWidget(self.status)
        self.cancel_button = GlassButton(self.t("cancel")); self.cancel_button.setObjectName("danger"); self.cancel_button.clicked.connect(self.cancel); processing_content_layout.addWidget(self.cancel_button, alignment=Qt.AlignmentFlag.AlignCenter)
        processing_layout.addWidget(self.processing_content, alignment=Qt.AlignmentFlag.AlignHCenter); processing_layout.addStretch(); self.workspace_stack.addWidget(self.processing_page)
        self.ready_page = QWidget(); self.ready_page.setObjectName("readyPage"); ready_layout = QVBoxLayout(self.ready_page); ready_layout.setContentsMargins(0, 12, 0, 12); ready_layout.setSpacing(14); self.workspace_stack.addWidget(self.ready_page)
        self.ready_title = QLabel(self.t("ready_title")); self.ready_title.setObjectName("readyTitle"); self.ready_title.setAlignment(Qt.AlignmentFlag.AlignCenter); ready_layout.addWidget(self.ready_title)
        self.ready_output = QLabel(self.t("completed")); self.ready_output.setObjectName("readyOutput"); self.ready_output.setWordWrap(True); self.ready_output.setAlignment(Qt.AlignmentFlag.AlignCenter); ready_layout.addWidget(self.ready_output)
        ready_actions = QHBoxLayout(); ready_actions.addStretch(); self.open_document_button = GlassButton(self.t("open_document")); self.open_document_button.setObjectName("primary"); self.open_document_button.clicked.connect(self._open_primary_export); ready_actions.addWidget(self.open_document_button)
        self.open_folder = GlassButton(self.t("open_folder")); self.open_folder.clicked.connect(self.open_output); ready_actions.addWidget(self.open_folder); ready_actions.addStretch(); ready_layout.addLayout(ready_actions)
        self.new_transcription_button = GlassButton(self.t("new_transcription")); self.new_transcription_button.clicked.connect(self._clear_source); ready_layout.addWidget(self.new_transcription_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        ready_layout.addStretch()
        self.footer = QLabel(f'Created by {CREATOR_NAME}  ·  <a href="mailto:{CONTACT_EMAIL}">Email</a>  ·  <a href="{SUPPORT_URL}">Support</a>')
        self.footer.setObjectName("metadata"); self.footer.setAlignment(Qt.AlignmentFlag.AlignCenter); self.footer.setOpenExternalLinks(False); self.footer.linkActivated.connect(self._open_external_url); console_layout.addWidget(self.footer)
        self._sync_empty_workspace()

    def _sync_empty_workspace(self) -> None:
        """Keep the central surface stable while its file state changes."""
        loaded = self.source is not None
        self.workspace_stack.setCurrentWidget(self.source_page if loaded else self.empty_page)
        self.clear_source_button.setVisible(loaded)
        if not loaded:
            self.file_label.setText(self.t("workspace_empty_title")); self.duration_label.setText(""); self.size_label.setText("")
            self.file_state.setText(self.t("workspace_empty_detail")); self.waveform.set_samples([])

    def _clear_source(self) -> None:
        if self._model_busy():
            return
        self._stop_waveform()
        self.source, self.duration, self.last_result = None, 0.0, None
        self.status.setText(""); self.progress.setValue(0); self.progress_percent.setText(""); self.progress_details.setText("")
        self._sync_empty_workspace(); self._refresh_profile()

    def _set_language(self, language: str) -> None:
        if self._model_busy() or self.translator.preference == language:
            return
        old_source, old_duration, old_result = self.source, self.duration, self.last_result
        self.settings.general.language = language; self.settings_store.save(self.settings); self.translator.set_language(language)
        self._build_ui(); self._show_device()
        if old_source:
            self.source, self.duration = old_source, old_duration; self.file_label.setText(old_source.name); self.duration_label.setText(f"{format_duration(old_duration)} ·"); self.size_label.setText(f"{old_source.stat().st_size / 1024 / 1024:.1f} MB")
            self.file_state.setText(self.t("file_ready")); self._sync_empty_workspace(); self._refresh_profile(); self._start_waveform(old_source, old_duration)
        if old_result:
            self.last_result = old_result; self._show_ready_result(old_result.exported)

    def _start_waveform(self, source: Path, duration: float) -> None:
        if self.waveform_thread is not None:
            if self.waveform_worker: self.waveform_worker.cancel()
            self.waveform_thread.quit(); self.waveform_thread.wait(300)
        self.waveform.set_loading(True); worker = WaveformWorker(source, duration); thread = QThread(self)
        self.waveform_worker, self.waveform_thread = worker, thread; worker.moveToThread(thread); thread.started.connect(worker.run)
        worker.ready.connect(lambda samples, expected=source: self._on_waveform_ready(expected, samples)); worker.failed.connect(lambda: self._on_waveform_failed(source))
        worker.ready.connect(thread.quit); worker.failed.connect(thread.quit); worker.cancelled.connect(thread.quit); thread.finished.connect(self._clear_waveform_worker); thread.start()

    def _stop_waveform(self) -> None:
        if self.waveform_worker: self.waveform_worker.cancel()
        if self.waveform_thread:
            self.waveform_thread.quit(); self.waveform_thread.wait(300)

    def _on_waveform_ready(self, source: Path, samples: list[float]) -> None:
        if self.source == source:
            self.waveform.set_samples(samples)

    def _on_waveform_failed(self, source: Path) -> None:
        if self.source == source:
            self.waveform.set_loading(False)

    def _clear_waveform_worker(self) -> None:
        if self.waveform_thread:
            self.waveform_thread.deleteLater()
        if self.waveform_worker:
            self.waveform_worker.deleteLater()
        self.waveform_thread = self.waveform_worker = None
    def _show_device(self) -> None:
        self.runtime = detect_gpu_runtime()
        self._refresh_profile()

    def _set_performance_profile(self) -> None:
        profile = self.mode_combo.currentData()
        if profile and profile != self.settings.recognition.performance_profile:
            self.settings.recognition.performance_profile = profile; self.settings_store.save(self.settings); self._refresh_profile()

    def _set_recognition_language(self) -> None:
        language = self.language_combo.currentData()
        if language and language != self.settings.recognition.language:
            self.settings.recognition.language = language; self.settings_store.save(self.settings)

    def _set_timestamps(self, enabled: bool) -> None:
        if enabled != self.settings.recognition.word_timestamps:
            self.settings.recognition.word_timestamps = enabled; self.settings_store.save(self.settings)

    def _toggle_theme(self) -> None:
        self._set_theme(self.theme_button.target_theme)

    def _set_theme(self, theme: str) -> None:
        if theme in {"dark", "light"} and theme != self.settings.general.theme:
            self.settings.general.theme = theme; self.settings_store.save(self.settings)
            ThemeManager.apply(QApplication.instance(), theme); self.theme_button.setCurrentTheme(theme)

    @staticmethod
    def _open_external_url(url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))
    def _refresh_profile(self) -> None:
        profile = resolve_profile(self.runtime, self.settings.recognition.performance_profile, self.settings.recognition.model, self.settings.recognition.vram_limit_mb, self.duration or None)
        if hasattr(self, "mode_combo"):
            self.mode_combo.blockSignals(True); self.mode_combo.setCurrentIndex(max(0, self.mode_combo.findData(self.settings.recognition.performance_profile))); self.mode_combo.blockSignals(False)
    def dragEnterEvent(self, event) -> None:
        if self._model_busy():
            event.ignore(); return
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile():
            self.drop_area.setProperty("dragActive", True); self.drop_area.update(); event.acceptProposedAction()
    def dragLeaveEvent(self, event) -> None:
        self.drop_area.setProperty("dragActive", False); self.drop_area.update(); event.accept()
    def dropEvent(self, event) -> None:
        if self._model_busy():
            event.ignore(); return
        urls = event.mimeData().urls()
        self.drop_area.setProperty("dragActive", False); self.drop_area.update()
        if urls: self.set_source(Path(urls[0].toLocalFile()))
    def select_file(self) -> None:
        patterns = " ".join(f"*{item}" for item in sorted(SUPPORTED_EXTENSIONS)); filters = f"{self.t('media_files')} ({patterns});;{self.t('all_files')} (*)"
        selected, _ = QFileDialog.getOpenFileName(self, self.t("choose_media"), str(Path.home()), filters)
        if selected: self.set_source(Path(selected))
    def set_source(self, source: Path) -> None:
        if self._model_busy():
            return
        try: duration = get_duration(source)
        except MediaError as error:
            logging.getLogger("transcripta").warning("Media selection failed: %s", error)
            self.source = None; self.duration = 0; self.file_label.setText(self.t("source_placeholder")); self.duration_label.setText(self.t("source_placeholder")); self.size_label.setText(self.t("source_placeholder")); QMessageBox.warning(self, self.t("file_error"), self.t(error.code)); return
        self.source, self.duration = source, duration; self.file_label.setText(source.name); self.duration_label.setText(f"{format_duration(duration)} ·"); self.size_label.setText(f"{source.stat().st_size / 1024 / 1024:.1f} MB"); self.file_state.setText(self.t("file_ready")); self.status.setText(""); self.last_result = None
        self._sync_empty_workspace(); self._refresh_profile(); self._start_waveform(source, duration)
    def start(self) -> None:
        if not self.source: QMessageBox.information(self, self.t("choose_file"), self.t("need_file")); return
        if self._model_busy(): return
        self.settings.recognition.language = self.language_combo.currentData()
        profile = resolve_profile(self.runtime, self.settings.recognition.performance_profile, self.settings.recognition.model, self.settings.recognition.vram_limit_mb, self.duration)
        if not self.model_manager.is_model_installed(profile.model_recommendation):
            confirmation = ModelDownloadConfirmationDialog(self.model_manager, profile.model_recommendation, self.t, self)
            if confirmation.exec() == QDialog.DialogCode.Accepted:
                self._pending_profile, self._pending_start = profile, True; self._begin_model_download(profile.model_recommendation)
            return
        self._start_transcription(profile)
    def _start_transcription(self, profile) -> None:
        self._stop_waveform(); self._last_progress = None; self._eta_seconds = None; self._active_profile = profile
        self.settings_store.save(self.settings); self.job = TranscriptionJob(self.source, self.duration, self.settings, APP_DATA_DIR, False, on_progress=lambda value: self.worker.progress.emit(value) if self.worker else None, on_warning=lambda value: self.worker.warning.emit(value) if self.worker else None, model_manager=self.model_manager)
        self.thread = QThread(self); self.worker = JobWorker(self.job, self.t("unknown_error")); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.progress.connect(self.on_progress); self.worker.warning.connect(self.on_warning); self.worker.finished.connect(self.on_finished); self.worker.cancelled.connect(self.on_cancelled); self.worker.failed.connect(self.on_failed)
        for signal in (self.worker.finished, self.worker.cancelled, self.worker.failed): signal.connect(self.thread.quit)
        self.thread.finished.connect(self._clear_worker); self.thread.start(); self._set_running(True)
        self.progress.setValue(0); self.progress_percent.setText("0%")
        self.progress_details.setText(self.t("progress_details", processed=format_duration(0), duration=format_duration(self.duration), eta=self.t("estimating")))
        self.status.setText("")
    def _model_busy(self) -> bool:
        return self.download_thread is not None or self.job is not None
    def _begin_model_download(self, label: str) -> None:
        if self.download_thread is not None: return
        self.download_dialog = ModelDownloadProgressDialog(self.model_manager, label, self.t, self)
        self.download_worker = ModelDownloadWorker(self.model_manager, label); self.download_thread = QThread(self); self.download_worker.moveToThread(self.download_thread)
        self.download_thread.started.connect(self.download_worker.run); self.download_worker.progress.connect(self.download_dialog.update_progress)
        # ``run`` occupies the worker event loop while HTTP reads are active.
        # Event.set is thread-safe, so cancellation must be delivered directly
        # from the dialog instead of waiting in that blocked event queue.
        self.download_dialog.cancelled_by_user.connect(self.download_worker.cancel, Qt.ConnectionType.DirectConnection)
        self.download_worker.completed.connect(self._on_model_downloaded); self.download_worker.cancelled.connect(self._on_model_download_cancelled); self.download_worker.failed.connect(self._on_model_download_failed)
        for signal in (self.download_worker.completed, self.download_worker.cancelled, self.download_worker.failed): signal.connect(self.download_thread.quit)
        self.download_thread.finished.connect(self._clear_download_worker); self.download_dialog.open(); self.download_thread.start()
    def _close_download_dialog(self) -> None:
        if self.download_dialog: self.download_dialog.done(QDialog.DialogCode.Accepted)
    def _on_model_downloaded(self, _path) -> None:
        self._close_download_dialog()
        if self._pending_start and self._pending_profile:
            profile, self._pending_profile, self._pending_start = self._pending_profile, None, False
            QTimer.singleShot(0, lambda: self._start_transcription(profile))
    def _on_model_download_cancelled(self) -> None:
        self._close_download_dialog(); self._pending_profile = None; self._pending_start = False; self.status.setText(self.t("download_cancelled"))
    def _on_model_download_failed(self) -> None:
        self._close_download_dialog(); label = self._pending_profile.model_recommendation if self._pending_profile else "large"
        answer = QMessageBox.warning(self, self.t("model_downloading"), self.t("download_failed"), QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Retry)
        if answer == QMessageBox.StandardButton.Retry:
            self._retry_download_label = label
        else:
            self._pending_profile = None; self._pending_start = False
    def _clear_download_worker(self) -> None:
        if self.download_thread: self.download_thread.deleteLater()
        if self.download_worker: self.download_worker.deleteLater()
        self.download_thread = self.download_worker = None
        if self._retry_download_label:
            label, self._retry_download_label = self._retry_download_label, None
            QTimer.singleShot(0, lambda: self._begin_model_download(label))
    def _set_running(self, running: bool) -> None:
        for item in (self.start_button, self.choose_button, self.mode_combo, self.language_combo): item.setEnabled(not running)
        if running:
            self.workspace_stack.setCurrentWidget(self.processing_page)
    def on_progress(self, progress: Progress) -> None:
        self._last_progress = progress; self._render_progress_status()
    def _render_progress_status(self) -> None:
        if not self._last_progress:
            return
        progress = self._last_progress; self.progress.setValue(round(progress.fraction * 100))
        observed = (progress.elapsed_seconds / progress.fraction - progress.elapsed_seconds) if progress.fraction else None
        if observed is not None and progress.elapsed_seconds >= 5 and progress.fraction >= .05:
            self._eta_seconds = observed if self._eta_seconds is None else .7 * self._eta_seconds + .3 * observed
        eta = format_duration(self._eta_seconds) if self._eta_seconds is not None else self.t("estimating")
        self.progress_percent.setText(f"{progress.fraction:.0%}")
        message = self.t("progress_details", processed=format_duration(progress.processed_seconds), duration=format_duration(progress.duration), eta=eta)
        self.progress_details.setText(message)
        self.status.setText("")
    def on_warning(self, message: str) -> None:
        self.status.setText(message)
    def toggle_pause(self) -> None:
        return
    def cancel(self) -> None:
        if self.job: self.job.cancel(); self.status.setText(self.t("cancelling"))
    def on_finished(self, result: JobResult) -> None:
        self.last_result = result; self.progress.setValue(100); self._set_running(False)
        self._show_ready_result(result.exported)
    def _show_ready_result(self, exported: dict[str, Path]) -> None:
        primary = exported.get("docx")
        self.ready_output.setText(self.t("completed"))
        self.open_document_button.setEnabled(primary is not None)
        self.workspace_stack.setCurrentWidget(self.ready_page)
    def on_cancelled(self) -> None:
        self._set_running(False); self._sync_empty_workspace()
    def on_failed(self, message: str) -> None:
        self._set_running(False); self._sync_empty_workspace(); QMessageBox.critical(self, self.t("error"), self.t("error_log_hint", message=message))
    def _clear_worker(self) -> None:
        if self.thread: self.thread.deleteLater()
        if self.worker: self.worker.deleteLater()
        self.thread = self.worker = self.job = None
    def open_output(self) -> None: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.settings.export.output_dir).resolve())))
    def _open_primary_export(self) -> None:
        self.open_export("docx")
    def open_export(self, name: str) -> None:
        if self.last_result and (target := self.last_result.exported.get(name)):
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

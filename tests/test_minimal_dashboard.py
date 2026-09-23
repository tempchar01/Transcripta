from __future__ import annotations

import os
import time
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt

from app.config.settings import SettingsStore
from app.ui.dashboard import CommandSurface, WaveformIcon
from app.ui.main_window import JobWorker, MainWindow
from app.ui.theme.manager import ThemeManager


def _window(tmp_path: Path) -> tuple[QApplication, MainWindow]:
    app = QApplication.instance() or QApplication([])
    return app, MainWindow(SettingsStore(tmp_path / "settings.json"))


def test_dashboard_is_a_single_compact_workspace_without_navigation_or_settings(tmp_path: Path) -> None:
    _app, window = _window(tmp_path)
    try:
        assert isinstance(window.console, CommandSurface)
        assert not window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert not window.centralWidget().testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert not window.testAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        assert window.console.objectName() == "commandSurface"
        assert window.language_combo.count() == 2
        assert isinstance(window.empty_icon, WaveformIcon)
        assert window.theme_button.toolTip() == window.t("switch_theme")
        assert window.empty_subhint.text() == window.t("drop_or_choose")
        assert not hasattr(window, "history_button")
        assert not hasattr(window, "result_tabs")
        assert not hasattr(window, "transcript_preview")
        assert not hasattr(window, "settings_button") and not hasattr(window, "timestamps_toggle")
        assert not hasattr(window, "settings_page")
        assert not hasattr(window, "content_stack")
        assert window.workspace_stack.currentWidget() is window.empty_page
        assert window.action_layout.alignment() & Qt.AlignmentFlag.AlignHCenter
        assert not hasattr(JobWorker, "preview")
        assert not hasattr(window, "on_preview")
        window.en_button.click()
        assert window.translator.preference == "en"
    finally:
        window.close()


def test_selected_audio_populates_real_waveform_without_blocking_ui(tmp_path: Path, synthetic_ogg: Path) -> None:
    app, window = _window(tmp_path)
    try:
        window.set_source(synthetic_ogg)
        deadline = time.monotonic() + 4
        while not window.waveform.samples and time.monotonic() < deadline:
            app.processEvents(); time.sleep(.02)
        assert len(window.waveform.samples) == 88
        assert max(window.waveform.samples) > min(window.waveform.samples)
        assert window.file_state.text() == window.t("file_ready")
    finally:
        if window.waveform_thread:
            window.waveform_thread.quit(); window.waveform_thread.wait(1000)
        window.close()


def test_ready_screen_has_only_result_actions_and_uses_real_export_targets(monkeypatch, tmp_path: Path) -> None:
    app, window = _window(tmp_path)
    opened: list[str] = []
    monkeypatch.setattr("app.ui.main_window.QDesktopServices.openUrl", lambda url: opened.append(url.toString()))
    exports = {"docx": tmp_path / "result.docx"}
    window.settings.export.output_dir = str(tmp_path)
    window.last_result = SimpleNamespace(exported=exports)
    try:
        window._show_ready_result(exports)
        assert window.workspace_stack.currentWidget() is window.ready_page
        assert window.ready_title.text() == window.t("ready_title")
        assert window.ready_output.text() == window.t("completed")
        assert not hasattr(window, "ready_duration")
        assert not hasattr(window, "ready_processing")
        assert not hasattr(window, "export_buttons")
        assert not hasattr(window, "transcript_preview")
        window.open_document_button.click(); window.open_folder.click(); window.new_transcription_button.click(); app.processEvents()
        assert opened[0].endswith("result.docx")
        assert opened[1].endswith(str(tmp_path.resolve()).replace("\\", "/"))
        assert window.workspace_stack.currentWidget() is window.empty_page
        assert window.source is None
    finally:
        window.close()


def test_processing_uses_a_legible_determinate_progress_surface(tmp_path: Path) -> None:
    _app, window = _window(tmp_path)
    try:
        window._set_running(True)
        assert not window.progress_percent.isHidden()
        assert not window.progress_details.isHidden()
        assert window.progress.minimumHeight() == 14
        assert window.progress.maximumHeight() == 14
        assert window.processing_content.maximumWidth() == 620
        assert not window.progress.isTextVisible()
        assert window.workspace_stack.currentWidget() is window.processing_page
    finally:
        window.close()


def test_theme_switch_persists_and_footer_links_use_vistarel_contacts(monkeypatch, tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    store = SettingsStore(tmp_path / "settings.json")
    settings = store.load(); settings.general.theme = "dark"; store.save(settings)
    window = MainWindow(store)
    opened: list[str] = []
    monkeypatch.setattr("app.ui.main_window.QDesktopServices.openUrl", lambda url: opened.append(url.toString()))
    try:
        window.mode_combo.setCurrentIndex(window.mode_combo.findData("maximum_speed"))
        window.language_combo.setCurrentIndex(window.language_combo.findData("auto"))
        assert not hasattr(window, "timestamps_toggle")
        assert window.settings.general.theme == "dark"
        assert window.theme_button.target_theme == "light"
        window.theme_button.click(); app.processEvents()
        assert window.settings.general.theme == "light"
        assert window.theme_button.target_theme == "dark"
        window.theme_button.click(); app.processEvents()
        assert window.settings.general.theme == "dark"
        assert "Created by Maksim Pershikov" in window.footer.text()
        assert 'href="mailto:tempchar1@outlook.com"' in window.footer.text()
        assert 'href="https://app.lava.top/tempchar"' in window.footer.text()
        assert not window.footer.openExternalLinks()
        window.footer.linkActivated.emit("mailto:tempchar1@outlook.com")
        window.footer.linkActivated.emit("https://app.lava.top/tempchar")
        assert opened == ["mailto:tempchar1@outlook.com", "https://app.lava.top/tempchar"]
    finally:
        window.close()
    restored = SettingsStore(tmp_path / "settings.json").load()
    assert restored.recognition.performance_profile == "maximum_speed"
    assert restored.recognition.language == "auto"
    assert restored.recognition.word_timestamps is False
    assert restored.general.theme == "dark"
    assert restored.export.output_dir
    _app, restored_window = _window(tmp_path)
    try:
        assert restored_window.settings.general.theme == "dark"
        assert restored_window.theme_button.target_theme == "light"
    finally:
        restored_window.close()


def test_minimal_themes_use_solid_surfaces_without_glass_gradients(tmp_path: Path) -> None:
    app, window = _window(tmp_path)
    try:
        for theme in ("dark", "light"):
            ThemeManager.apply(app, theme)
            stylesheet = app.styleSheet().lower()
            assert "qlineargradient" not in stylesheet
            assert "qradialgradient" not in stylesheet
            assert "rgba(" not in stylesheet
            assert "commandSurface" in app.styleSheet()
    finally:
        window.close()

"""Command Glass dialogs and worker for first-use ASR model downloads."""
from __future__ import annotations

import logging
import threading
import time

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDialogButtonBox, QLabel, QProgressBar, QVBoxLayout

from app.transcription.model_manager import ModelDownloadCancelled, ModelManager
from app.ui.components.cards import GlassButton, GlassDialog


def format_size(size_bytes: int | None) -> str:
    if size_bytes is None:
        return "—"
    return f"{size_bytes / (1024 * 1024):.0f} MB" if size_bytes < 1024 ** 3 else f"{size_bytes / (1024 ** 3):.1f} GB"


class ModelDownloadWorker(QObject):
    progress = Signal(object, object)
    completed = Signal(object)
    cancelled = Signal()
    failed = Signal()

    def __init__(self, manager: ModelManager, label: str) -> None:
        super().__init__(); self.manager, self.label, self.cancel_token = manager, label, threading.Event()

    def cancel(self) -> None:
        self.cancel_token.set()

    def run(self) -> None:
        try:
            self.completed.emit(self.manager.download_model(self.label, self.progress.emit, self.cancel_token))
        except ModelDownloadCancelled:
            self.cancelled.emit()
        except Exception:
            logging.getLogger("transcripta").exception("Model download failed for %s", self.label)
            self.failed.emit()


class ModelDownloadConfirmationDialog(GlassDialog):
    def __init__(self, manager: ModelManager, label: str, translate, parent=None) -> None:
        super().__init__(parent); self.setWindowTitle(translate("model_required")); self.setMinimumWidth(470)
        spec = manager.spec(label); layout = QVBoxLayout(self)
        message = QLabel(translate("model_required_message", model=spec.friendly_name, size=f"≈ {spec.estimated_size_mb / 1024:.1f} GB", path=manager.get_model_path_text(label)))
        message.setWordWrap(True); layout.addWidget(message)
        buttons = QDialogButtonBox(); self.download_button = GlassButton(translate("download_continue")); cancel = GlassButton(translate("cancel_dialog"))
        self.download_button.clicked.connect(self.accept); cancel.clicked.connect(self.reject); buttons.addButton(self.download_button, QDialogButtonBox.ButtonRole.AcceptRole); buttons.addButton(cancel, QDialogButtonBox.ButtonRole.RejectRole); layout.addWidget(buttons)


class ModelDownloadProgressDialog(GlassDialog):
    cancelled_by_user = Signal()

    def __init__(self, manager: ModelManager, label: str, translate, parent=None) -> None:
        super().__init__(parent); self.setWindowTitle(translate("model_downloading")); self.setMinimumWidth(430); self.setModal(True)
        spec = manager.spec(label); layout = QVBoxLayout(self)
        self.message = QLabel(translate("model_downloading_message", model=spec.friendly_name)); self.message.setWordWrap(True); layout.addWidget(self.message)
        self.progress = QProgressBar(); self.progress.setRange(0, 0); layout.addWidget(self.progress)
        self.detail = QLabel(translate("download_progress_unknown")); self.detail.setObjectName("muted"); layout.addWidget(self.detail)
        self.cancel_button = GlassButton(translate("cancel")); self.cancel_button.clicked.connect(self._cancel); layout.addWidget(self.cancel_button)
        self.t = translate; self.cancel_requested = False
        self._started_at = time.monotonic(); self._last_bytes: int | None = None; self._last_at = self._started_at

    def update_progress(self, downloaded: int | None, total: int | None) -> None:
        now = time.monotonic()
        speed = None
        if downloaded is not None and self._last_bytes is not None and now > self._last_at:
            speed = max(0.0, (downloaded - self._last_bytes) / (now - self._last_at))
        if downloaded is not None:
            self._last_bytes, self._last_at = downloaded, now
        if total and total > 0:
            self.progress.setRange(0, 100); self.progress.setValue(min(100, round((downloaded or 0) * 100 / total)))
            eta = "—" if not speed else self.t("download_eta_seconds", seconds=max(0, round((total - (downloaded or 0)) / speed)))
            rate = self.t("download_speed", speed=format_size(int(speed))) if speed else self.t("download_speed_unknown")
            self.detail.setText(self.t("download_progress", downloaded=format_size(downloaded), total=format_size(total)) + f" · {rate} · {eta}")
        else:
            self.progress.setRange(0, 0); self.detail.setText(self.t("download_progress_unknown"))

    def _cancel(self) -> None:
        if not self.cancel_requested:
            self.cancel_requested = True; self.cancel_button.setEnabled(False); self.detail.setText(self.t("download_cancelling")); self.cancelled_by_user.emit()

    def reject(self) -> None:
        self._cancel()

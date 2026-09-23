from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PySide6 = pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from app.config.settings import SettingsStore
from app.hardware.gpu import GpuRuntime
from app.ui.main_window import MainWindow
from app.transcription.model_manager import ModelDownloadCancelled
from app.branding import PRODUCT_NAME
import app.ui.main_window as main_window_module


def test_gui_hides_development_models_and_policy_details(monkeypatch, tmp_path):
    runtime = GpuRuntime(True, "NVIDIA Test", 16 * 1024, "1", True, True, ("float16", "int8_float16"), "cuda")
    monkeypatch.setattr("app.ui.main_window.detect_gpu_runtime", lambda: runtime)
    application = QApplication.instance() or QApplication([])
    window = MainWindow(SettingsStore(tmp_path / "settings.json"))
    try:
        assert not hasattr(window, "model_combo")
        assert window.windowTitle() == "Transcripta"
        assert not hasattr(window, "model_label")
        assert not hasattr(window, "recommendation_label")
    finally:
        window.close()
        application.processEvents()


def test_gui_accepts_ogg_with_no_external_ffmpeg(monkeypatch, tmp_path, synthetic_ogg):
    runtime = GpuRuntime(False, None, None, None, False, False, (), "cpu")
    source = synthetic_ogg
    assert source.is_file()
    monkeypatch.setattr("app.ui.main_window.detect_gpu_runtime", lambda: runtime)
    monkeypatch.setattr("app.audio.media.resolve_ffmpeg_binary", lambda _: None)
    application = QApplication.instance() or QApplication([])
    window = MainWindow(SettingsStore(tmp_path / "settings.json"))
    try:
        window.set_source(source)
        assert window.source == source
        assert window.duration > 0
        assert window.file_label.text() == source.name
    finally:
        window.close(); application.processEvents()


class _Manager:
    def __init__(self, installed: bool) -> None:
        self.installed = installed
    def is_model_installed(self, _label): return self.installed
    def get_model_size(self, _label): return None
    def get_model_path_text(self, _label): return "C:/controlled/models"
    def spec(self, label): return SimpleNamespace(label=label, friendly_name="Large-v3", estimated_size_mb=3100)
    def delete_model(self, _label): self.deleted = True; return True


def _window_with_manager(monkeypatch, tmp_path, installed: bool):
    manager = _Manager(installed)
    runtime = GpuRuntime(True, "NVIDIA Test", 16 * 1024, "1", True, True, ("float16",), "cuda")
    monkeypatch.setattr("app.ui.main_window.detect_gpu_runtime", lambda: runtime)
    monkeypatch.setattr("app.ui.main_window.ModelManager", lambda _path: manager)
    application = QApplication.instance() or QApplication([])
    window = MainWindow(SettingsStore(tmp_path / "settings.json")); window.source = tmp_path / "synthetic.ogg"; window.duration = 1.0
    return application, window, manager


def test_installed_model_starts_asr_without_dialog(monkeypatch, tmp_path):
    application, window, _manager = _window_with_manager(monkeypatch, tmp_path, True)
    started = []
    monkeypatch.setattr(window, "_start_transcription", lambda profile: started.append(profile.model_recommendation))
    try:
        window.start()
        assert started == ["large"]
    finally:
        window.close(); application.processEvents()


@pytest.mark.parametrize("accepted, expected", [(True, ["large"]), (False, [])])
def test_missing_model_confirmation_controls_pending_download(monkeypatch, tmp_path, accepted, expected):
    application, window, _manager = _window_with_manager(monkeypatch, tmp_path, False)
    class Confirmation:
        def __init__(self, *_args): pass
        def exec(self): return 1 if accepted else 0
    requested = []
    monkeypatch.setattr(main_window_module, "ModelDownloadConfirmationDialog", Confirmation)
    monkeypatch.setattr(window, "_begin_model_download", lambda label: requested.append(label))
    try:
        window.start()
        assert requested == expected
    finally:
        window.close(); application.processEvents()


def test_download_success_automatically_starts_pending_transcription(monkeypatch, tmp_path):
    application, window, _manager = _window_with_manager(monkeypatch, tmp_path, False)
    profile = SimpleNamespace(model_recommendation="large")
    window._pending_profile, window._pending_start = profile, True
    started = []
    monkeypatch.setattr(window, "_start_transcription", lambda result: started.append(result))
    try:
        window._on_model_downloaded(None); application.processEvents()
        assert started == [profile]
    finally:
        window.close(); application.processEvents()


def test_download_failure_offers_friendly_retry(monkeypatch, tmp_path):
    application, window, _manager = _window_with_manager(monkeypatch, tmp_path, False)
    window._pending_profile = SimpleNamespace(model_recommendation="large")
    requested, messages = [], []
    monkeypatch.setattr(main_window_module.QTimer, "singleShot", lambda _delay, callback: callback())
    monkeypatch.setattr(main_window_module.QMessageBox, "warning", lambda *_args: (messages.append(_args[2]) or main_window_module.QMessageBox.StandardButton.Retry))
    monkeypatch.setattr(window, "_begin_model_download", lambda label: requested.append(label))
    try:
        window._on_model_download_failed()
        window._clear_download_worker()
        assert requested == ["large"]
        assert messages == [window.t("download_failed")]
    finally:
        window.close(); application.processEvents()


def test_download_cancel_reaches_busy_worker_without_waiting_for_its_event_loop(monkeypatch, tmp_path):
    """The worker thread is busy inside download_model, so cancel must be direct."""
    application, window, _manager = _window_with_manager(monkeypatch, tmp_path, False)

    class BlockingManager(_Manager):
        def __init__(self):
            super().__init__(False); self.started = threading.Event()

        def download_model(self, _label, _progress, token):
            self.started.set()
            while not token.wait(0.01):
                pass
            raise ModelDownloadCancelled()

    manager = BlockingManager()
    window.model_manager = manager
    try:
        window._begin_model_download("large")
        deadline = time.monotonic() + 2
        while not manager.started.is_set() and time.monotonic() < deadline:
            application.processEvents(); time.sleep(0.01)
        assert manager.started.is_set()
        window.download_dialog._cancel()
        assert not window.download_dialog.cancel_button.isEnabled()
        assert window.download_dialog.detail.text() == window.t("download_cancelling")
        deadline = time.monotonic() + 2
        while window.download_thread is not None and time.monotonic() < deadline:
            application.processEvents(); time.sleep(0.01)
        assert window.download_thread is None
        assert window.status.text() == window.t("download_cancelled")
    finally:
        if window.download_thread:
            window.download_thread.quit(); window.download_thread.wait(1000)
        window.close(); application.processEvents()

"""Internal packaged acceptance probe. No UI modifications or substituted ASR."""
from __future__ import annotations

import importlib.metadata
import json
import os
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path


def run(config_path: str) -> int:
    config = json.loads(Path(config_path).read_text(encoding="utf-8-sig"))
    destination = Path(config["report"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    report = {"passed": False, "frozen": bool(getattr(sys, "frozen", False)),
              "executable": sys.executable, "python": sys.version, "mode": config.get("mode", "gui")}
    window = None
    try:
        from app.release import VERSION
        from app.hardware.gpu import detect_gpu_runtime
        from app.hardware.nvidia_runtime import discover_nvidia_runtime_paths
        from app.config.settings import APP_DATA_DIR, SettingsStore
        report["version"] = VERSION
        report["app_data"] = str(APP_DATA_DIR)
        report["runtime"] = detect_gpu_runtime().to_dict()
        report["dll_directories"] = [str(p) for p in discover_nvidia_runtime_paths()[0]]
        report["packages"] = {p: importlib.metadata.version(p) for p in
                              ("PySide6", "faster-whisper", "ctranslate2", "av", "numpy", "onnxruntime", "python-docx")}
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer
        from app.branding import application_icon
        from app.ui.main_window import MainWindow
        app = QApplication.instance() or QApplication([])
        app.setWindowIcon(application_icon())
        window = MainWindow(SettingsStore())
        window.setWindowIcon(app.windowIcon())
        window.show()
        app.processEvents()
        assert not app.windowIcon().isNull(), "Packaged app icon missing"
        assert not hasattr(window, "transcript_preview")
        assert not hasattr(window, "history_button")
        report["surface_backend"] = window._surface_backend
        report["icon_loaded"] = True
        if config.get("download_model"):
            model = config["download_model"]
            window.model_manager.download_model(model)
            report["downloaded_model_bytes"] = window.model_manager.get_model_size(model)
        if config.get("audio"):
            window.set_source(Path(config["audio"]))
            assert window.source is not None and window.duration > 0, "Input failed to load"
            report["audio_duration_seconds"] = window.duration
            window.settings.recognition.performance_profile = "balanced"
            window.settings.export.output_dir = str(Path(config["output"]).resolve())
            Path(config["output"]).mkdir(parents=True, exist_ok=True)
            window.settings_store.save(window.settings)
            # Start through the unchanged UI's real production job wiring.
            started = time.monotonic()
            window.start()
            if window.worker is None:
                raise RuntimeError("No worker started; required production model is missing")
            errors = []
            window.worker.failed.connect(errors.append)
            def check_finished():
                if errors or (window.last_result is not None and window.thread is None):
                    app.quit()
                elif time.monotonic() - started > config.get("timeout_seconds", 1800):
                    window.cancel()
                    errors.append("Inference timeout")
            timer = QTimer()
            timer.timeout.connect(check_finished)
            timer.start(100)
            app.exec()
            timer.stop()
            if errors:
                raise RuntimeError(errors[0])
            result = window.last_result
            assert result is not None, "No result"
            report.update(device=result.device, gpu_inference_succeeded=result.gpu_inference_succeeded,
                          processing_seconds=result.processing_seconds, segments=len(result.transcript.segments),
                          coverage=asdict(result.coverage), decode=asdict(result.decode_diagnostics),
                          exports={k: str(v) for k, v in result.exported.items()})
            assert result.device == "cuda" and result.gpu_inference_succeeded, "Actual CUDA inference required"
            assert result.transcript.segments, "Transcript is empty"
            for path in result.exported.values():
                assert path.is_file() and path.stat().st_size > 0
            from docx import Document
            assert any(p.text.strip() for p in Document(result.exported["docx"]).paragraphs)
            assert window.workspace_stack.currentWidget() is window.ready_page
            report["ready_visible"] = True
            report["settings_persisted"] = SettingsStore().load().export.output_dir == window.settings.export.output_dir
        else:
            assert not hasattr(window, "settings_page")
            assert not hasattr(window, "content_stack")
            assert window.workspace_stack.currentWidget() is window.empty_page
            assert window.new_transcription_button.text()
            report["single_screen"] = True
        if config.get("screenshot"):
            app.processEvents()
            assert window.grab().save(config["screenshot"])
        report["passed"] = True
    except Exception:
        report["error"] = traceback.format_exc()
    finally:
        if window is not None and window.job is None:
            window.close()
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return 0 if report["passed"] else 1

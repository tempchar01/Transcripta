from __future__ import annotations

import importlib.metadata
import importlib.util
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.hardware import nvidia_runtime


class FakeDistribution:
    def __init__(self, root: Path) -> None:
        self.root = root

    def locate_file(self, relative: Path) -> Path:
        return self.root / relative


def test_discovers_package_local_nvidia_dll_paths(monkeypatch, tmp_path):
    cublas = tmp_path / "nvidia" / "cublas" / "bin"; cublas.mkdir(parents=True)
    cudnn = tmp_path / "nvidia" / "cudnn" / "bin"; cudnn.mkdir(parents=True)
    ctranslate2 = tmp_path / "ctranslate2"; ctranslate2.mkdir()
    (ctranslate2 / "cudnn64_9.dll").touch()
    distributions = {"nvidia-cublas-cu12": FakeDistribution(tmp_path), "nvidia-cudnn-cu12": FakeDistribution(tmp_path), "ctranslate2": FakeDistribution(tmp_path)}
    monkeypatch.setattr(nvidia_runtime.importlib.metadata, "distribution", lambda name: distributions[name])
    found, missing = nvidia_runtime.discover_nvidia_runtime_paths()
    assert found == (cublas.resolve(), cudnn.resolve(), ctranslate2.resolve())
    assert missing == ()


def test_missing_runtime_packages_are_reported(monkeypatch):
    def absent(_name):
        raise importlib.metadata.PackageNotFoundError
    monkeypatch.setattr(nvidia_runtime.importlib.metadata, "distribution", absent)
    found, missing = nvidia_runtime.discover_nvidia_runtime_paths()
    assert found == ()
    assert set(missing) == {"nvidia-cublas-cu12", "nvidia-cudnn-cu12", "ctranslate2"}


def test_missing_bundled_cudnn_runtime_is_reported(monkeypatch, tmp_path):
    monkeypatch.setattr(nvidia_runtime.importlib.metadata, "distribution", lambda name: FakeDistribution(tmp_path))
    found, missing = nvidia_runtime.discover_nvidia_runtime_paths()
    assert found == ()
    assert "ctranslate2 bundled cuDNN" in missing


def test_windows_activation_keeps_handles_and_logs(monkeypatch, tmp_path, caplog):
    directory = (tmp_path / "nvidia" / "cublas" / "bin"); directory.mkdir(parents=True)
    monkeypatch.setenv("PATH", os.environ.get("PATH", ""))
    monkeypatch.setattr(nvidia_runtime, "discover_nvidia_runtime_paths", lambda: ((directory,), ("nvidia-cudnn-cu12",)))
    handles: list[str] = []
    monkeypatch.setattr(nvidia_runtime.os, "name", "nt")
    monkeypatch.setattr(nvidia_runtime.os, "add_dll_directory", lambda path: handles.append(path) or object(), raising=False)
    monkeypatch.setattr(nvidia_runtime, "_ACTIVE_PATHS", set())
    monkeypatch.setattr(nvidia_runtime, "_DLL_DIRECTORY_HANDLES", [])
    monkeypatch.setattr(nvidia_runtime, "_PROCESS_PATHS", set())
    caplog.set_level(logging.INFO, logger="transcripta")
    result = nvidia_runtime.activate_nvidia_runtime_paths(logging.getLogger("transcripta"))
    assert result.activated == (directory,)
    assert handles == [str(directory)]
    assert "Activated NVIDIA runtime DLL directory" in caplog.text
    assert "Added NVIDIA runtime directory to the current process PATH" in caplog.text
    assert str(directory) in os.environ["PATH"]
    assert nvidia_runtime._DLL_DIRECTORY_HANDLES


@pytest.mark.gpu_runtime
def test_clean_subprocess_activates_runtime_without_manual_path():
    if not all(importlib.util.find_spec(name) for name in ("ctranslate2", "nvidia.cublas")):
        pytest.skip("GPU runtime packages are not installed in this interpreter")
    environment = os.environ.copy()
    environment["PATH"] = ";".join(item for item in environment.get("PATH", "").split(";") if "nvidia\\cublas\\bin" not in item.lower())
    result = subprocess.run([sys.executable, "-c", "from app.hardware.gpu import detect_gpu_runtime; print(detect_gpu_runtime().actual_backend)"],
                            cwd=Path(__file__).parents[1], env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "cuda"

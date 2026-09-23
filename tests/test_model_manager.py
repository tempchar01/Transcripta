from __future__ import annotations

import threading
from pathlib import Path

import pytest

from app.transcription.model_manager import (ModelDownloadCancelled, ModelManager,
                                             ModelUnavailableError, REQUIRED_MODEL_FILES)


def _snapshot_path(cache: Path, label: str = "large") -> Path:
    model_id = ModelManager(cache).model_id(label)
    return cache / f"models--Systran--faster-whisper-{model_id}" / "snapshots" / "test-revision"


def _write_valid_snapshot(cache: Path, label: str = "large") -> Path:
    snapshot = _snapshot_path(cache, label); snapshot.mkdir(parents=True)
    for name in REQUIRED_MODEL_FILES:
        (snapshot / name).write_bytes(b"model")
    return snapshot


def test_download_validates_snapshot_and_is_detected_after_restart(tmp_path):
    calls: list[dict] = []
    def download(**kwargs):
        calls.append(kwargs); return _write_valid_snapshot(Path(kwargs["cache_dir"]))

    manager = ModelManager(tmp_path, snapshot_download=download)
    progress: list[tuple[int | None, int | None]] = []
    path = manager.download_model("large", lambda done, total: progress.append((done, total)))
    assert manager.is_model_installed("large-v3")
    assert manager.validate_model("large", path)
    assert manager.get_model_size("large") == len(REQUIRED_MODEL_FILES) * len(b"model")
    assert calls[0]["repo_id"] == "Systran/faster-whisper-large-v3"
    assert calls[0]["local_files_only"] is False
    assert progress[0] == (0, None) and progress[-1][0] == progress[-1][1]
    assert ModelManager(tmp_path).is_model_installed("large")


def test_incomplete_or_failed_download_is_not_installed(tmp_path):
    def broken(**kwargs):
        snapshot = _snapshot_path(Path(kwargs["cache_dir"])); snapshot.mkdir(parents=True)
        (snapshot / "config.json").write_text("{}")
        (snapshot / "model.bin").write_bytes(b"incomplete")
        return snapshot

    manager = ModelManager(tmp_path, snapshot_download=broken)
    with pytest.raises(ModelUnavailableError):
        manager.download_model("large")
    assert not manager.is_model_installed("large")


def test_download_cancel_removes_new_partial_cache(tmp_path):
    token = threading.Event()
    def cancellable(**kwargs):
        progress = kwargs["tqdm_class"](total=10)
        progress.update(1)
        return _write_valid_snapshot(Path(kwargs["cache_dir"]))

    def on_progress(done, _total):
        if done == 0:
            token.set()

    manager = ModelManager(tmp_path, snapshot_download=cancellable)
    with pytest.raises(ModelDownloadCancelled):
        manager.download_model("large", on_progress, token)
    assert not manager.is_model_installed("large")


def test_delete_model_removes_only_configured_repository(tmp_path):
    _write_valid_snapshot(tmp_path)
    unrelated = tmp_path / "unrelated"; unrelated.mkdir(); (unrelated / "keep.txt").write_text("keep")
    manager = ModelManager(tmp_path)
    assert manager.delete_model("large")
    assert not manager.is_model_installed("large")
    assert (unrelated / "keep.txt").is_file()

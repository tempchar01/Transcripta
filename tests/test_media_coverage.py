from __future__ import annotations

import wave
from pathlib import Path

import pytest

from app.audio.media import logical_coverage, stream_chunks
from app.config.settings import AppSettings
from app.hardware.gpu import GpuRuntime
from app.jobs.checkpoint import CheckpointStore
from app.jobs.runner import TranscriptionJob


def _pcm_48khz(path: Path, seconds: int = 61) -> Path:
    """A deterministic multi-chunk fixture that forces PyAV 48 kHz -> 16 kHz resampling."""
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1); output.setsampwidth(2); output.setframerate(48_000)
        output.writeframes(b"\x00\x00" * 48_000 * seconds)
    return path


def test_pyav_chunk_pcm_uses_sample_count_not_aligned_plane_size(tmp_path: Path) -> None:
    source = _pcm_48khz(tmp_path / "long.wav")
    chunks = list(stream_chunks(source, tmp_path / "chunks", 61.0, 30, overlap_seconds=8))
    try:
        assert [(chunk.content_start, chunk.content_end) for chunk in chunks] == [(0.0, 30.0), (30.0, 60.0), (60.0, 61.0)]
        assert [round(chunk.duration, 3) for chunk in chunks] == [30.0, 38.0, 9.0]
        coverage = logical_coverage(((chunk.content_start, chunk.content_end) for chunk in chunks), 61.0)
        assert coverage.covered_duration == 61.0 and not coverage.gaps
    finally:
        for chunk in chunks:
            chunk.path.unlink(missing_ok=True)


def test_logical_coverage_handles_overlap_and_reports_real_gaps() -> None:
    complete = logical_coverage(((0.0, 300.0), (292.0, 600.0), (592.0, 780.0)), 780.0)
    assert complete.covered_duration == 780.0 and complete.gaps == ()
    incomplete = logical_coverage(((0.0, 300.0), (320.0, 780.0)), 780.0)
    assert incomplete.covered_duration == 760.0 and incomplete.gaps == ((300.0, 320.0),)


def test_failed_chunk_cannot_be_checkpointed_as_completed(monkeypatch, synthetic_wav: Path, tmp_path: Path) -> None:
    runtime = GpuRuntime(True, "Test GPU", 16 * 1024, "1", True, True, ("float16",), "cuda")
    monkeypatch.setattr("app.jobs.runner.detect_gpu_runtime", lambda: runtime)

    class FailingModel:
        def transcribe(self, *_args, **_kwargs):
            raise RuntimeError("decode failed")

    class Manager:
        def load(self, *_args, **_kwargs):
            return FailingModel()

    settings = AppSettings(); settings.recognition.chunk_seconds = 30
    job = TranscriptionJob(synthetic_wav, 1.0, settings, tmp_path, False, model_manager=Manager())
    with pytest.raises(RuntimeError, match="chunk 1 was not processed"):
        job.run()
    checkpoint = CheckpointStore(job._job_directory() / "checkpoint.json").load()
    assert checkpoint is None or (checkpoint.next_offset_seconds == 0 and checkpoint.completed_chunks == [])

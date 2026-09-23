import logging

import pytest
from types import SimpleNamespace

from app.audio.media import AudioChunk
from app.config.settings import AppSettings
from app.hardware.gpu import GpuRuntime
from app.jobs.runner import JobCancelled, TranscriptionJob


def test_cancelled_job_stops_at_safe_boundary(synthetic_wav, tmp_path):
    job = TranscriptionJob(synthetic_wav, 1.0, AppSettings(), tmp_path, allow_download=False)
    job.cancel()
    with pytest.raises(JobCancelled):
        job._wait_if_paused()


def test_cancel_after_checkpoint_does_not_extract_a_new_temporary_chunk(monkeypatch, synthetic_wav, tmp_path, caplog):
    runtime = GpuRuntime(True, "Test GPU", 16 * 1024, "1", True, True, ("float16", "int8_float16"), "cuda")
    monkeypatch.setattr("app.jobs.runner.detect_gpu_runtime", lambda: runtime)
    calls: list[int] = []
    chunks_requested: list[int] = []
    chunk_path = tmp_path / "chunk_0.wav"; chunk_path.write_bytes(b"fixture")
    chunk = AudioChunk(0, 0.0, 1.0, chunk_path, 0.0, 1.0)

    def chunks(*_args, **_kwargs):
        calls.append(1)
        chunks_requested.append(_args[3])
        return iter([chunk])

    monkeypatch.setattr("app.jobs.runner.stream_chunks", chunks)
    monkeypatch.setattr("app.jobs.runner.export_docx", lambda *_args, **_kwargs: {})
    readable_calls: list[object] = []
    monkeypatch.setattr("app.jobs.runner.build_readable_transcript", lambda transcript: readable_calls.append(transcript))

    class Model:
        def transcribe(self, *_args, **_kwargs):
            return iter([SimpleNamespace(start=0.1, end=0.8, text="тест", avg_logprob=-0.1, words=[])]), SimpleNamespace()

    class Manager:
        def load(self, *_args, **_kwargs):
            return Model()

    job: TranscriptionJob
    def progress(_value):
        job.cancel()
    settings = AppSettings(); settings.recognition.chunk_seconds = 45
    caplog.set_level(logging.INFO, logger="transcripta")
    job = TranscriptionJob(synthetic_wav, 2.0, settings, tmp_path, False, on_progress=progress, model_manager=Manager())
    with pytest.raises(JobCancelled):
        job.run()
    assert calls == [1]
    assert chunks_requested == [45]
    assert not chunk_path.exists()
    assert readable_calls == []
    assert "Selected: large-v3 / float16; GPU: Test GPU; VRAM: 16384 MB; Reason:" in caplog.text


def test_readable_transcript_is_built_once_only_after_complete_coverage(monkeypatch, synthetic_wav, tmp_path):
    runtime = GpuRuntime(True, "Test GPU", 16 * 1024, "1", True, True, ("float16",), "cuda")
    monkeypatch.setattr("app.jobs.runner.detect_gpu_runtime", lambda: runtime)
    chunk = AudioChunk(0, 0.0, 1.0, synthetic_wav, 0.0, 1.0)
    monkeypatch.setattr("app.jobs.runner.stream_chunks", lambda *_args, **_kwargs: iter([chunk]))
    monkeypatch.setattr("app.jobs.runner.export_docx", lambda *_args, **_kwargs: {})
    calls = []
    from app.transcription.readable import build_readable_transcript as real_builder
    def builder(transcript):
        calls.append(transcript)
        return real_builder(transcript)
    monkeypatch.setattr("app.jobs.runner.build_readable_transcript", builder)

    class Model:
        def transcribe(self, *_args, **_kwargs):
            return iter([SimpleNamespace(start=0.0, end=.8, text="Готовый текст.", avg_logprob=-.1, words=[])]), SimpleNamespace()
    class Manager:
        def load(self, *_args, **_kwargs): return Model()

    result = TranscriptionJob(synthetic_wav, 1.0, AppSettings(), tmp_path, False, model_manager=Manager()).run()
    assert len(calls) == 1
    assert result.readable_transcript.plain_text == "Готовый текст."

from pathlib import Path
from types import SimpleNamespace

from app.audio.media import AudioChunk
from app.config.settings import AppSettings
from app.hardware.gpu import GpuRuntime
from app.jobs.checkpoint import CheckpointStore, JobCheckpoint
from app.jobs.runner import TranscriptionJob


class RetryModel:
    def __init__(self, fail: bool) -> None:
        self.fail = fail

    def transcribe(self, *_args, **_kwargs):
        if self.fail:
            raise RuntimeError("CUDA out of memory")
        return iter([SimpleNamespace(start=0.1, end=0.8, text=" тест ", avg_logprob=-0.1, words=[])]), SimpleNamespace()


class RetryManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def load(self, _model, device, compute, _allow_download, **_kwargs):
        self.calls.append((device, compute))
        return RetryModel(len(self.calls) == 1)


class StableManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def load(self, _model, device, compute, _allow_download, **_kwargs):
        self.calls.append((device, compute))
        return RetryModel(False)


def test_oom_retries_current_chunk_then_checkpoints_and_resumes(monkeypatch, synthetic_wav, tmp_path):
    runtime = GpuRuntime(True, "Test GPU", 16 * 1024, "1", True, True, ("float16", "int8_float16", "int8"), "cuda")
    monkeypatch.setattr("app.jobs.runner.detect_gpu_runtime", lambda: runtime)
    temporary_chunk = tmp_path / "chunk.wav"
    temporary_chunk.write_bytes(b"fixture")
    chunk = AudioChunk(0, 0.0, 1.0, temporary_chunk, 0.0, 1.0)
    monkeypatch.setattr("app.jobs.runner.stream_chunks", lambda *_args, **_kwargs: iter([chunk]))
    monkeypatch.setattr("app.jobs.runner.export_docx", lambda *_args, **_kwargs: {})
    monkeypatch.setattr("app.jobs.runner.CheckpointStore.clear", lambda _store: None)
    settings = AppSettings(); settings.recognition.model = "large"; settings.recognition.performance_profile = "auto"
    checkpoint_path = tmp_path / "jobs" / "placeholder" / "checkpoint.json"
    manager = RetryManager()
    job = TranscriptionJob(synthetic_wav, 1.0, settings, tmp_path, False, model_manager=manager)
    result = job.run()
    assert manager.calls == [("cuda", "float16"), ("cuda", "int8_float16")]
    assert result.gpu_inference_succeeded is True
    assert result.transcript.segments[0].text == "тест"
    assert result.hardware_profile.compute_type == "int8_float16"
    persisted = CheckpointStore(job._job_directory() / "checkpoint.json").load()
    assert persisted is not None and persisted.next_offset_seconds == 1.0
    assert persisted.hardware_profile is not None
    assert persisted.hardware_profile["compute_type"] == "int8_float16"
    resumed_manager = StableManager()
    resumed = TranscriptionJob(synthetic_wav, 1.0, settings, tmp_path, False, model_manager=resumed_manager).run()
    assert resumed.recovered_from_checkpoint is True
    assert resumed_manager.calls == [("cuda", "int8_float16")]


def test_advanced_precision_override_is_passed_to_model(monkeypatch, synthetic_wav, tmp_path):
    runtime = GpuRuntime(True, "Test GPU", 16 * 1024, "1", True, True, ("float16", "int8_float16"), "cuda")
    monkeypatch.setattr("app.jobs.runner.detect_gpu_runtime", lambda: runtime)
    chunk = AudioChunk(0, 0.0, 1.0, synthetic_wav, 0.0, 1.0)
    monkeypatch.setattr("app.jobs.runner.stream_chunks", lambda *_args, **_kwargs: iter([chunk]))
    monkeypatch.setattr("app.jobs.runner.export_docx", lambda *_args, **_kwargs: {})
    monkeypatch.setattr("app.jobs.runner.CheckpointStore.clear", lambda _store: None)
    settings = AppSettings(); settings.recognition.compute_type = "int8_float16"
    manager = StableManager()
    result = TranscriptionJob(synthetic_wav, 1.0, settings, tmp_path, False, model_manager=manager).run()
    assert manager.calls == [("cuda", "int8_float16")]
    assert result.hardware_profile.compute_type == "int8_float16"

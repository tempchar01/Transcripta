"""Single, controlled model-cache boundary for local ASR models."""
from __future__ import annotations

import threading
import os
import shutil
import time
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.hardware.nvidia_runtime import activate_nvidia_runtime_paths


MODEL_IDS = {"small": "small", "medium": "medium", "large": "large-v3"}
MODEL_SIZE_MB = {"small": 500, "medium": 1_600, "large": 3_100}
MODEL_REPOSITORIES = {label: f"Systran/faster-whisper-{model_id}" for label, model_id in MODEL_IDS.items()}
REQUIRED_MODEL_FILES = ("config.json", "model.bin", "tokenizer.json")
ProgressCallback = Callable[[int | None, int | None], None]


class ModelUnavailableError(RuntimeError):
    pass


class ModelDownloadCancelled(RuntimeError):
    pass


class ModelState(str, Enum):
    MISSING = "missing"
    DOWNLOADING = "downloading"
    PARTIAL = "partial"
    VALIDATING = "validating"
    INSTALLED = "installed"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ModelSpec:
    label: str
    model_id: str
    repository: str
    estimated_size_mb: int

    @property
    def friendly_name(self) -> str:
        return "Large-v3" if self.label == "large" else self.model_id.capitalize()


class ModelManager:
    """Owns installed-model discovery, HTTPS download, validation and removal.

    The GUI never calls Hugging Face directly. ``snapshot_download`` retains TLS
    verification and stores partial downloads outside a validated snapshot.
    """
    def __init__(self, cache_dir: Path, snapshot_download=None) -> None:
        self.cache_dir = Path(cache_dir)
        self._snapshot_download = snapshot_download
        self._states: dict[str, ModelState] = {}

    def available_models(self) -> list[ModelSpec]:
        return [self.spec(label) for label in MODEL_IDS]

    def spec(self, label_or_id: str) -> ModelSpec:
        label = self._label(label_or_id)
        return ModelSpec(label, MODEL_IDS[label], MODEL_REPOSITORIES[label], MODEL_SIZE_MB[label])

    def _label(self, label_or_id: str) -> str:
        if label_or_id in MODEL_IDS:
            return label_or_id
        for label, model_id in MODEL_IDS.items():
            if label_or_id == model_id:
                return label
        raise ValueError(f"Неизвестная модель: {label_or_id}")

    def model_id(self, label: str) -> str:
        return self.spec(label).model_id

    def estimated_size_mb(self, label: str) -> int:
        return self.spec(label).estimated_size_mb

    def get_model_size(self, label: str) -> int | None:
        path = self.get_model_path(label)
        if not path:
            return None
        return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())

    def _repository_dir(self, label: str) -> Path:
        return self.cache_dir / f"models--{self.spec(label).repository.replace('/', '--')}"

    def _snapshot_paths(self, label: str) -> list[Path]:
        snapshots = self._repository_dir(label) / "snapshots"
        return sorted((path for path in snapshots.iterdir() if path.is_dir()), key=lambda path: path.stat().st_mtime, reverse=True) if snapshots.is_dir() else []

    def get_model_path(self, label: str) -> Path | None:
        return next((path for path in self._snapshot_paths(label) if self.validate_model(label, path)), None)

    def is_model_installed(self, label: str) -> bool:
        return self.get_model_path(label) is not None

    def is_installed(self, label: str) -> bool:
        """Compatibility name for existing callers."""
        return self.is_model_installed(label)

    def state(self, label: str) -> ModelState:
        """Return a truthful cache/download state; only validated snapshots install."""
        normalized = self._label(label)
        active = self._states.get(normalized)
        if active in {ModelState.DOWNLOADING, ModelState.VALIDATING, ModelState.ERROR}:
            return active
        if self.is_model_installed(normalized):
            return ModelState.INSTALLED
        repository = self._repository_dir(normalized)
        return ModelState.PARTIAL if repository.exists() and any(repository.rglob("*")) else ModelState.MISSING

    def _set_state(self, label: str, state: ModelState) -> None:
        self._states[self._label(label)] = state

    def validate_model(self, label: str, path: Path | None = None) -> bool:
        self.spec(label)
        candidate = path
        if candidate is None:
            snapshots = self._snapshot_paths(label)
            candidate = snapshots[0] if snapshots else None
        return bool(candidate and candidate.is_dir() and all((candidate / name).is_file() for name in REQUIRED_MODEL_FILES))

    def get_model_path_text(self, label: str) -> str:
        return str(self.get_model_path(label) or (self._repository_dir(label) / "snapshots"))

    def _download_function(self):
        if self._snapshot_download is not None:
            return self._snapshot_download
        # hf_xet can download successfully on Windows while bypassing tqdm
        # entirely. That leaves the GUI frozen at 0 MB and prevents a timely
        # cancellation. The standard HTTPS client reports byte progress and
        # uses the Python/OpenSSL transport verified by this application.
        os.environ["HF_HUB_DISABLE_XET"] = "1"
        from huggingface_hub import snapshot_download
        return snapshot_download

    @staticmethod
    def _download_model_binary(spec: ModelSpec, snapshot: Path, callback: ProgressCallback,
                               token: threading.Event) -> None:
        """Stream the large model payload through Python HTTPS with resume/cancel.

        The Hub's native Xet client can transfer bytes without forwarding them
        to ``tqdm_class``.  This direct, signed-redirect-aware request keeps
        the GUI's byte count, speed and cancellation truthful on Windows.
        """
        import httpx

        target = snapshot / "model.bin"
        partial = snapshot / "model.bin.part"
        if target.is_file():
            return
        start = partial.stat().st_size if partial.is_file() else 0
        url = f"https://huggingface.co/{spec.repository}/resolve/main/model.bin"
        timeout = httpx.Timeout(connect=20.0, read=60.0, write=20.0, pool=20.0)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            headers = {"Range": f"bytes={start}-"} if start else {}
            with client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()
                if start and response.status_code != 206:
                    start = 0
                    partial.unlink(missing_ok=True)
                length = response.headers.get("content-length")
                total = (start + int(length)) if length and length.isdigit() else None
                callback(start, total)
                mode, written, reported_at = ("ab" if start else "wb"), start, time.monotonic()
                with partial.open(mode) as output:
                    for block in response.iter_bytes(chunk_size=1024 * 1024):
                        if token.is_set():
                            raise ModelDownloadCancelled()
                        output.write(block)
                        written += len(block)
                        now = time.monotonic()
                        if written - start >= 2 * 1024 * 1024 or now - reported_at >= 0.2:
                            output.flush()
                            callback(written, total)
                            start, reported_at = written, now
                    output.flush()
                callback(written, total)
        if total is not None and written != total:
            raise ModelUnavailableError("Model transfer ended before the expected byte count.")
        partial.replace(target)

    def download_model(self, label: str, progress_callback: ProgressCallback | None = None,
                       cancel_token: threading.Event | None = None) -> Path:
        """Download one configured official model repository over the hub's HTTPS client."""
        spec, callback, token = self.spec(label), progress_callback or (lambda _done, _total: None), cancel_token or threading.Event()
        if token.is_set():
            raise ModelDownloadCancelled()
        self._set_state(spec.label, ModelState.DOWNLOADING)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        callback(0, None)
        from tqdm.auto import tqdm

        class DownloadProgress(tqdm):
            def __init__(self, *args, **kwargs) -> None:
                kwargs["disable"] = True
                super().__init__(*args, **kwargs)
                callback(self.n, self.total)

            def update(self, amount=1):
                if token.is_set():
                    raise ModelDownloadCancelled()
                result = super().update(amount)
                callback(self.n, self.total)
                return result

        try:
            snapshot = Path(self._download_function()(repo_id=spec.repository, cache_dir=str(self.cache_dir),
                                                       local_files_only=False, tqdm_class=DownloadProgress,
                                                       allow_patterns=("*.json", "*.txt", ".gitattributes", "README.md")))
            self._download_model_binary(spec, snapshot, callback, token)
            if token.is_set():
                raise ModelDownloadCancelled()
            self._set_state(spec.label, ModelState.VALIDATING)
            if not self.validate_model(spec.label, snapshot):
                raise ModelUnavailableError("Downloaded model snapshot did not pass validation.")
            size = self.get_model_size(spec.label)
            callback(size, size)
            self._set_state(spec.label, ModelState.INSTALLED)
            return snapshot
        except ModelDownloadCancelled:
            # Hugging Face stores blobs atomically and resumes them safely.
            # Keep a partial cache, but never classify it as installed.
            self._set_state(spec.label, ModelState.PARTIAL)
            raise
        except ModelUnavailableError:
            # A transfer that finished but cannot satisfy the model contract is
            # not resumable. Remove only its invalid snapshots, never another
            # model repository.
            self._remove_invalid_snapshots(spec.label)
            self._set_state(spec.label, ModelState.ERROR)
            raise
        except Exception as error:
            # Transport errors may leave a valid ``.part`` payload. Preserve it
            # for the next controlled resume rather than pretending it is an
            # installed model or throwing away user bandwidth.
            self._set_state(spec.label, ModelState.ERROR)
            raise ModelUnavailableError("Model download failed.") from error

    def _remove_invalid_snapshots(self, label: str) -> None:
        for path in self._snapshot_paths(label):
            if not self.validate_model(label, path):
                shutil.rmtree(path, ignore_errors=True)

    def delete_model(self, label: str) -> bool:
        """Remove the configured model repository from the controlled cache only."""
        directory = self._repository_dir(label)
        if not directory.exists():
            return False
        shutil.rmtree(directory)
        return True

    def load(self, label: str, device: str, compute_type: str, allow_download: bool = False, *,
             cpu_threads: int = 4, num_workers: int = 1):
        """Load a validated local snapshot; optional CLI download stays inside this manager."""
        activate_nvidia_runtime_paths()
        try:
            from faster_whisper import WhisperModel
        except ImportError as error:
            raise ModelUnavailableError("faster-whisper не установлен. Выполните установку зависимостей из README.") from error
        if not self.is_model_installed(label):
            if not allow_download:
                raise ModelUnavailableError("Модель распознавания не установлена.")
            self.download_model(label)
        model_path = self.get_model_path(label)
        if model_path is None:
            raise ModelUnavailableError("Модель распознавания не прошла проверку.")
        selected_device = "cuda" if device == "cuda" else "cpu"
        selected_compute = compute_type if compute_type != "auto" else ("float16" if selected_device == "cuda" else "int8")
        try:
            return WhisperModel(str(model_path), device=selected_device, compute_type=selected_compute,
                                cpu_threads=max(1, cpu_threads), num_workers=1,
                                local_files_only=True)
        except Exception as error:
            raise ModelUnavailableError("Не удалось открыть установленную модель распознавания.") from error

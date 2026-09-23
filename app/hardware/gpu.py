from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass

from app.hardware.nvidia_runtime import activate_nvidia_runtime_paths


def _command_output(command: list[str]) -> str | None:
    if not shutil.which(command[0]):
        return None
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout.strip() if completed.returncode == 0 and completed.stdout.strip() else None


@dataclass(frozen=True, slots=True)
class GpuRuntime:
    """Each capability is independently observed; detected is not equivalent to usable."""
    gpu_detected: bool
    gpu_name: str | None
    total_vram_mb: int | None
    driver_version: str | None
    cuda_runtime_detected: bool
    ctranslate2_cuda_usable: bool
    supported_compute_types: tuple[str, ...]
    actual_backend: str
    reason: str | None = None

    @property
    def effective_vram_mb(self) -> int | None:
        return self.total_vram_mb

    def to_dict(self) -> dict:
        return asdict(self)


def detect_gpu_runtime() -> GpuRuntime:
    """Probe NVIDIA and CTranslate2 separately without starting a model inference."""
    activate_nvidia_runtime_paths()
    output = _command_output([
        "nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"
    ])
    name: str | None = None
    vram: int | None = None
    driver: str | None = None
    if output:
        fields = [item.strip() for item in output.splitlines()[0].split(",")]
        name = fields[0] if fields else None
        try:
            vram = int(fields[1])
        except (IndexError, ValueError):
            pass
        driver = fields[2] if len(fields) > 2 else None

    try:
        import ctranslate2

        types = tuple(sorted(ctranslate2.get_supported_compute_types("cuda")))
        return GpuRuntime(
            gpu_detected=bool(name), gpu_name=name, total_vram_mb=vram, driver_version=driver,
            cuda_runtime_detected=bool(types), ctranslate2_cuda_usable=bool(types),
            supported_compute_types=types, actual_backend="cuda" if types else "cpu",
            reason=None if types else "CTranslate2 returned no CUDA compute types.",
        )
    except Exception as error:  # Runtime DLL errors are meaningful diagnostics, not failures of detection.
        return GpuRuntime(
            gpu_detected=bool(name), gpu_name=name, total_vram_mb=vram, driver_version=driver,
            cuda_runtime_detected=False, ctranslate2_cuda_usable=False, supported_compute_types=(),
            actual_backend="cpu", reason=f"CTranslate2 CUDA unavailable: {error}",
        )


def system_summary() -> dict[str, str]:
    return {"os": platform.platform(), "python": platform.python_version()}

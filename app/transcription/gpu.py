from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    cuda_available: bool
    device: str
    name: str | None = None
    vram_mib: int | None = None
    ctranslate2_cuda: bool = False
    reason: str | None = None


def detect_device() -> DeviceInfo:
    """Detect actual usable CTranslate2 CUDA capability, not merely an installed GPU."""
    name: str | None = None
    vram: int | None = None
    if shutil.which("nvidia-smi"):
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode == 0 and result.stdout.strip():
            values = [value.strip() for value in result.stdout.splitlines()[0].split(",")]
            name = values[0]
            try:
                vram = int(values[1])
            except (IndexError, ValueError):
                pass
    try:
        import ctranslate2  # lazy: UI must start before optional dependencies are installed
        compute_types = ctranslate2.get_supported_compute_types("cuda")
        if compute_types:
            return DeviceInfo(True, "cuda", name, vram, True)
        return DeviceInfo(False, "cpu", name, vram, False, "CTranslate2 CUDA backend недоступен")
    except Exception as error:  # CUDA loader messages vary by driver/runtime
        return DeviceInfo(False, "cpu", name, vram, False, str(error))

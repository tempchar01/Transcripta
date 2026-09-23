from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum

from app.hardware.gpu import GpuRuntime


class PerformanceProfile(StrEnum):
    ECO = "eco"
    BALANCED = "balanced"
    MAXIMUM_SPEED = "maximum_speed"
    # Read legacy settings/checkpoints without changing their semantics unexpectedly.
    AUTO = "auto"
    FAST = "fast"
    MEMORY_SAVER = "memory_saver"
    QUALITY = "quality"
    CPU = "cpu"


@dataclass(frozen=True, slots=True)
class HardwareProfile:
    name: PerformanceProfile
    device: str
    total_vram_mb: int | None
    compute_type: str
    batch_size: int
    model_recommendation: str
    max_workers: int
    cpu_threads: int
    vad_enabled: bool
    chunk_seconds: int
    overlap_seconds: int
    context_mode: str
    notes: tuple[str, ...]
    simulated_vram_mb: int | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["name"] = self.name.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "HardwareProfile":
        restored = dict(data)
        restored["name"] = PerformanceProfile(restored["name"])
        restored["notes"] = tuple(restored.get("notes", ()))
        return cls(**restored)


def _supported(preferred: str, available: tuple[str, ...], fallback: str) -> str:
    if preferred in available:
        return preferred
    if fallback in available:
        return fallback
    return available[0] if available else fallback


def _vram_class(runtime: GpuRuntime, vram_limit_mb: int | None) -> int:
    vram = vram_limit_mb if vram_limit_mb is not None else runtime.effective_vram_mb
    if not vram:
        return 0
    if vram <= 6_500:
        return 6
    if vram <= 9_000:
        return 8
    if vram <= 13_500:
        return 12
    return 16


def resolve_profile(runtime: GpuRuntime, requested: str = "auto", model: str = "auto",
                    vram_limit_mb: int | None = None, audio_duration_seconds: float | None = None) -> HardwareProfile:
    """Select bounded, serial inference settings from observed runtime capabilities.

    batch_size remains 1 intentionally: WhisperModel is used serially; claiming a larger
    batch without switching to BatchedInferencePipeline would be a fake performance knob.
    """
    try:
        profile = PerformanceProfile(requested)
    except ValueError:
        profile = PerformanceProfile.AUTO
    available = runtime.supported_compute_types
    vram_class = _vram_class(runtime, vram_limit_mb)
    simulated = vram_limit_mb if vram_limit_mb is not None else None
    if profile is PerformanceProfile.CPU or not runtime.ctranslate2_cuda_usable:
        chosen = model if model != "auto" else "small"
        return HardwareProfile(PerformanceProfile.CPU, "cpu", runtime.total_vram_mb, "int8", 1, chosen, 1, 4, True, 300, 0,
                               "none", ("CPU mode: GPU-specific parameters are disabled.",), simulated)

    # New named modes keep one model instance and one ASR worker.  Legacy
    # values remain intact so existing settings and checkpoints behave as before.
    default_model = "large" if vram_class >= 12 else "medium"
    chosen = default_model if model == "auto" else model
    if profile is PerformanceProfile.ECO:
        return HardwareProfile(profile, "cuda", runtime.total_vram_mb, _supported("int8_float16", available, "int8"), 1,
                               chosen, 1, 4, True, 300, 8, "previous_chunk_tail",
                               ("Eco keeps one serial large-v3 job while reserving CPU and VRAM headroom.",), simulated)
    if profile is PerformanceProfile.MAXIMUM_SPEED:
        return HardwareProfile(profile, "cuda", runtime.total_vram_mb, _supported("float16", available, "int8_float16"), 1,
                               chosen, 1, 8, True, 900, 8, "previous_chunk_tail",
                               ("Maximum Speed keeps one serial ASR worker and favours throughput.",), simulated)
    if profile is PerformanceProfile.BALANCED:
        return HardwareProfile(profile, "cuda", runtime.total_vram_mb, _supported("float16", available, "int8_float16"), 1,
                               chosen, 1, 4, True, 900, 8, "previous_chunk_tail",
                               ("Balanced keeps large-v3 quality and reserves CPU headroom for Windows.",), simulated)

    if profile is PerformanceProfile.MEMORY_SAVER:
        chosen = model if model != "auto" else ("medium" if vram_class >= 6 else "small")
        return HardwareProfile(profile, "cuda", runtime.total_vram_mb, _supported("int8_float16", available, "int8"), 1,
                               chosen, 1, 4, True, 300, 8, "previous_chunk_tail",
                               ("Memory-saving profile uses short chunks and serial inference.",), simulated)
    if profile is PerformanceProfile.FAST:
        chosen = model if model != "auto" else "small"
        return HardwareProfile(profile, "cuda", runtime.total_vram_mb, _supported("float16", available, "int8_float16"), 1,
                               chosen, 1, 8, True, 300, 6, "previous_chunk_tail",
                               ("Fast profile prioritizes throughput; it is not the Russian-quality default.",), simulated)
    if profile is PerformanceProfile.QUALITY:
        chosen = model if model != "auto" else "large"
        return HardwareProfile(profile, "cuda", runtime.total_vram_mb, _supported("float16", available, "int8_float16"), 1,
                               chosen, 1, 8, True, 900, 8, "previous_chunk_tail",
                               ("Quality profile may not fit on 6–8 GB GPUs.",), simulated)

    # Quality-first AUTO: large-v3 is the default only where measured headroom is sufficient.
    if vram_class <= 6:
        recommendation, compute, chunk, note = "medium", _supported("int8_float16", available, "int8"), 300, "6 GB class: Large is not selected automatically."
    elif vram_class <= 8:
        recommendation, compute, chunk, note = "medium", _supported("float16", available, "int8_float16"), 600, "8 GB class: Medium is the quality/safety default."
    else:
        recommendation, compute, chunk, note = "large", _supported("float16", available, "int8_float16"), 900, "12+ GB VRAM: large-v3 is the quality-default policy."
    if audio_duration_seconds and audio_duration_seconds >= 3 * 3600:
        chunk = min(chunk, 600)
        note += " Long audio uses at most 600-second chunks; model choice remains quality-led."
    chosen = recommendation if model == "auto" else model
    warnings = [note]
    if chosen == "large" and vram_class <= 8:
        warnings.append("Large was selected manually on limited VRAM; OOM downgrade is armed.")
    return HardwareProfile(profile if profile is PerformanceProfile.BALANCED else PerformanceProfile.AUTO, "cuda", runtime.total_vram_mb,
                           compute, 1, chosen, 1, 4, True, chunk, 8, "previous_chunk_tail", tuple(warnings), simulated)


def downgrade_profile(current: HardwareProfile, attempt: int) -> HardwareProfile | None:
    """Bounded OOM degradation: precision, then smaller chunks, then CPU."""
    if current.device == "cpu":
        return None
    if attempt == 1 and current.compute_type == "float16":
        return HardwareProfile(**{**current.to_dict(), "name": PerformanceProfile.MEMORY_SAVER, "compute_type": "int8_float16",
                                  "chunk_seconds": min(current.chunk_seconds, 600), "notes": current.notes + ("OOM retry: float16 to int8_float16.",)})
    if attempt == 1 and current.compute_type != "int8":
        return HardwareProfile(**{**current.to_dict(), "name": PerformanceProfile.MEMORY_SAVER, "compute_type": "int8",
                                  "chunk_seconds": min(current.chunk_seconds, 600), "notes": current.notes + ("OOM retry: compute type to int8.",)})
    if attempt == 2:
        return HardwareProfile(**{**current.to_dict(), "name": PerformanceProfile.MEMORY_SAVER,
                                  "chunk_seconds": max(120, current.chunk_seconds // 2),
                                  "notes": current.notes + ("OOM retry: shorter chunks for subsequent decoding.",)})
    if attempt == 3:
        return HardwareProfile(PerformanceProfile.CPU, "cpu", current.total_vram_mb, "int8", 1,
                               current.model_recommendation, 1, 4, current.vad_enabled, 300, 0, "none",
                               current.notes + ("GPU OOM persisted: CPU fallback selected.",), current.simulated_vram_mb)
    return None

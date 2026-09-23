from app.hardware.gpu import GpuRuntime
from app.hardware.profiles import PerformanceProfile, downgrade_profile, resolve_profile


def runtime(vram: int | None, types: tuple[str, ...] = ("float16", "int8_float16", "int8")) -> GpuRuntime:
    return GpuRuntime(True, "NVIDIA Test", vram, "1.0", True, True, types, "cuda")


def test_6gb_auto_is_conservative():
    profile = resolve_profile(runtime(6 * 1024), "auto", "auto")
    assert profile.model_recommendation == "medium"
    assert profile.compute_type == "int8_float16"
    assert profile.chunk_seconds == 300


def test_8gb_auto_prefers_medium():
    profile = resolve_profile(runtime(8 * 1024), "auto", "auto")
    assert profile.model_recommendation == "medium"
    assert profile.compute_type == "float16"
    assert profile.chunk_seconds == 600


def test_12gb_auto_uses_quality_default():
    profile = resolve_profile(runtime(12 * 1024), "auto", "auto")
    assert profile.model_recommendation == "large"
    assert profile.compute_type == "float16"


def test_16gb_auto_uses_large_quality_default():
    profile = resolve_profile(runtime(16 * 1024), "auto", "auto")
    assert profile.model_recommendation == "large"
    assert profile.batch_size == 1


def test_named_profiles_keep_serial_large_v3_and_bound_cpu_threads():
    eco = resolve_profile(runtime(16 * 1024), "eco", "auto")
    balanced = resolve_profile(runtime(16 * 1024), "balanced", "auto")
    maximum = resolve_profile(runtime(16 * 1024), "maximum_speed", "auto")
    assert (eco.model_recommendation, balanced.model_recommendation, maximum.model_recommendation) == ("large", "large", "large")
    assert (eco.max_workers, balanced.max_workers, maximum.max_workers) == (1, 1, 1)
    assert eco.compute_type == "int8_float16"
    assert balanced.compute_type == maximum.compute_type == "float16"
    assert (eco.cpu_threads, balanced.cpu_threads, maximum.cpu_threads) == (4, 4, 8)
    assert balanced.chunk_seconds == maximum.chunk_seconds == 900


def test_auto_uses_shorter_chunks_for_very_long_audio():
    profile = resolve_profile(runtime(16 * 1024), "auto", "auto", audio_duration_seconds=3 * 3600)
    assert profile.model_recommendation == "large"
    assert profile.chunk_seconds == 600


def test_quality_explicitly_selects_large():
    profile = resolve_profile(runtime(16 * 1024), "quality", "auto")
    assert profile.model_recommendation == "large"


def test_fast_prepares_throughput_mode_without_ui_exposure():
    profile = resolve_profile(runtime(16 * 1024), "fast", "auto")
    assert profile.name is PerformanceProfile.FAST
    assert profile.model_recommendation == "small"


def test_compute_type_falls_back_to_available_type():
    profile = resolve_profile(runtime(8 * 1024, ("int8",)), "auto", "auto")
    assert profile.compute_type == "int8"


def test_cpu_fallback_does_not_use_gpu_settings():
    unavailable = GpuRuntime(False, None, None, None, False, False, (), "cpu", "not installed")
    profile = resolve_profile(unavailable, "auto", "auto")
    assert profile.name is PerformanceProfile.CPU
    assert profile.compute_type == "int8"
    assert profile.overlap_seconds == 0


def test_oom_downgrade_is_bounded_and_reaches_cpu():
    profile = resolve_profile(runtime(16 * 1024), "auto", "large")
    first = downgrade_profile(profile, 1)
    second = downgrade_profile(first, 2)
    third = downgrade_profile(second, 3)
    assert first.compute_type == "int8_float16"
    assert second.chunk_seconds < first.chunk_seconds
    assert third.device == "cpu"
    assert downgrade_profile(third, 4) is None

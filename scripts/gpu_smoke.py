from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from app.hardware.gpu import detect_gpu_runtime
from app.utils.metrics import gpu_used_memory_mb, peak_process_ram_mb


def _duration_with_pyav(path: Path) -> float:
    try:
        import av
        with av.open(str(path)) as container:
            if container.duration is not None:
                return float(container.duration / av.time_base)
    except Exception as error:
        raise RuntimeError(f"PyAV could not read the input audio: {error}") from error
    raise RuntimeError("PyAV did not expose a media duration.")


def run_smoke(audio: Path, model_name: str, compute_type: str, allow_model_download: bool) -> dict:
    """Run a real CUDA-only smoke test. It never substitutes CPU on failure."""
    runtime_before = detect_gpu_runtime()
    report: dict = {
        "gpu_runtime_before": runtime_before.to_dict(), "model": model_name, "compute_type": compute_type,
        "model_loaded_on_cuda": False, "gpu_inference_passed": False, "device_actually_used": None,
    }
    if not runtime_before.ctranslate2_cuda_usable:
        report["error"] = "CTranslate2 CUDA backend is unavailable; CPU fallback is intentionally not attempted."
        return report
    if not audio.is_file():
        report["error"] = f"Audio file does not exist: {audio}"
        return report
    try:
        from faster_whisper import WhisperModel
        started = time.monotonic()
        model = WhisperModel(model_name, device="cuda", compute_type=compute_type,
                             download_root=str(Path.home() / ".transcripta" / "models"),
                             local_files_only=not allow_model_download)
        report["model_load_seconds"] = round(time.monotonic() - started, 3)
        report["model_loaded_on_cuda"] = True
        report["audio_duration_seconds"] = _duration_with_pyav(audio)
        peak_vram = gpu_used_memory_mb()
        started = time.monotonic()
        segments, info = model.transcribe(str(audio), language="ru", beam_size=5, vad_filter=True)
        text_parts = [segment.text.strip() for segment in segments if segment.text.strip()]
        report["processing_seconds"] = round(time.monotonic() - started, 3)
        report["realtime_factor"] = round(report["processing_seconds"] / report["audio_duration_seconds"], 4)
        report["peak_ram_mb"] = peak_process_ram_mb()
        samples = [value for value in (peak_vram, gpu_used_memory_mb()) if value is not None]
        report["peak_vram_mb_sampled"] = max(samples) if samples else None
        report["segments"] = len(text_parts)
        report["recognized_text"] = " ".join(text_parts)
        report["detected_language"] = getattr(info, "language", None)
        report["gpu_inference_passed"] = True
        report["device_actually_used"] = "cuda"
    except Exception as error:
        report["error"] = str(error)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a real CUDA-only faster-whisper speech smoke test.")
    parser.add_argument("audio", type=Path, help="Short real speech audio; Russian is expected.")
    parser.add_argument("--model", choices=("tiny", "small", "medium", "large-v3"), default="tiny")
    parser.add_argument("--compute", choices=("float16", "int8_float16"), default="float16")
    parser.add_argument("--allow-model-download", action="store_true", help="Explicitly allow downloading a missing model.")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    report = run_smoke(args.audio, args.model, args.compute, args.allow_model_download)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("gpu_inference_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())

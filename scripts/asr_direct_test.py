"""Measure the complete PyAV decode and run one direct local faster-whisper control pass.

This bypasses Transcripta's chunk, checkpoint, deduplication, export and GUI layers.
It is intentionally a diagnostic command, not a production transcription entry point.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from app.audio.media import assert_supported
from app.config.settings import APP_DATA_DIR
from app.transcription.model_manager import ModelManager
from app.utils.metrics import gpu_used_memory_mb, peak_process_ram_mb


def probe_pyav_decode(source: Path) -> dict[str, object]:
    """Count decoded, resampled PCM samples; duration metadata is reported separately."""
    import av

    with av.open(str(source), mode="r") as container:
        stream = next((item for item in container.streams if item.type == "audio"), None)
        if stream is None:
            raise RuntimeError("No audio stream was found.")
        container_duration = float(container.duration / av.time_base) if container.duration else None
        stream_duration = float(stream.duration * stream.time_base) if stream.duration is not None and stream.time_base else None
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16_000)
        decoded_frames = decoded_source_samples = decoded_output_samples = 0
        first_frame_time = last_frame_time = None
        source_rates: set[int] = set()
        for frame in container.decode(stream):
            decoded_frames += 1
            decoded_source_samples += frame.samples
            source_rates.add(frame.sample_rate)
            frame_start = float(frame.time) if frame.time is not None else None
            frame_end = frame_start + frame.samples / frame.sample_rate if frame_start is not None else None
            first_frame_time = frame_start if first_frame_time is None else first_frame_time
            last_frame_time = frame_end if frame_end is not None else last_frame_time
            decoded_output_samples += sum(converted.samples for converted in resampler.resample(frame))
        decoded_output_samples += sum(converted.samples for converted in resampler.resample(None))
    return {
        "container_duration_seconds": container_duration,
        "stream_index": stream.index,
        "stream_duration_seconds": stream_duration,
        "stream_sample_rate": stream.rate,
        "decoded_frames": decoded_frames,
        "decoded_source_samples": decoded_source_samples,
        "decoded_source_rates": sorted(source_rates),
        "decoded_output_samples": decoded_output_samples,
        "decoded_output_sample_rate": 16_000,
        "decoded_duration_seconds": decoded_output_samples / 16_000,
        "first_decoded_frame_seconds": first_frame_time,
        "last_decoded_frame_seconds": last_frame_time,
    }


def run_direct(source: Path, model_label: str, compute_type: str, language: str, vad_filter: bool) -> dict[str, object]:
    manager = ModelManager(APP_DATA_DIR / "models")
    baseline_vram = gpu_used_memory_mb()
    loaded = time.monotonic()
    model = manager.load(model_label, "cuda", compute_type, allow_download=False)
    model_load_seconds = time.monotonic() - loaded
    started = time.monotonic()
    segments, info = model.transcribe(str(source), language=None if language == "auto" else language,
                                      beam_size=5, vad_filter=vad_filter, word_timestamps=False)
    materialized = list(segments)
    processing_seconds = time.monotonic() - started
    text = " ".join(item.text.strip() for item in materialized if item.text.strip())
    used_samples = [value for value in (baseline_vram, gpu_used_memory_mb()) if value is not None]
    return {
        "model": manager.model_id(model_label),
        "compute_type": compute_type,
        "device": "cuda",
        "vad_filter": vad_filter,
        "model_load_seconds": model_load_seconds,
        "processing_seconds": processing_seconds,
        "detected_language": getattr(info, "language", None),
        "segments": len(materialized),
        "first_timestamp_seconds": materialized[0].start if materialized else None,
        "last_timestamp_seconds": materialized[-1].end if materialized else None,
        "recognized_text_characters": len(text),
        "recognized_text": text,
        "peak_ram_mb": peak_process_ram_mb(),
        "peak_vram_mb_sampled": max(used_samples) if used_samples else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--model", choices=("small", "medium", "large"), default="large")
    parser.add_argument("--compute", choices=("float16", "int8_float16"), default="float16")
    parser.add_argument("--language", default="ru")
    parser.add_argument("--no-vad", action="store_true", help="Diagnostic control: disable faster-whisper VAD.")
    parser.add_argument("--decode-only", action="store_true", help="Measure PyAV decode only; do not load a model.")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    assert_supported(args.audio)
    report = {"source": str(args.audio.resolve()), "decode": probe_pyav_decode(args.audio)}
    if args.decode_only:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    try:
        report["direct_asr"] = run_direct(args.audio, args.model, args.compute, args.language, not args.no_vad)
    except Exception as error:
        report["error"] = str(error)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

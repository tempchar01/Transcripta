from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import wave
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Iterable, Iterator


SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".opus", ".mp4", ".mkv", ".mov", ".webm"}
FFMPEG_DIRECTORY_ENV = "TRANSCRIPTA_FFMPEG_DIR"
_configured_ffmpeg_directory: Path | None = None
PCM_SAMPLE_RATE = 16_000
CHUNK_DURATION_TOLERANCE_SECONDS = 0.25


class MediaError(RuntimeError):
    """A safe, user-facing media failure; backend detail belongs in logs."""
    def __init__(self, message: str, code: str = "media_open") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class DecodeDiagnostics:
    container_duration: float | None
    stream_duration: float | None
    stream_index: int
    stream_sample_rate: int | None
    decoded_frames: int
    decoded_source_samples: int
    decoded_output_samples: int
    decoded_output_sample_rate: int
    decoded_duration: float
    first_frame_time: float | None
    last_frame_time: float | None


@dataclass(frozen=True, slots=True)
class Coverage:
    covered_duration: float
    gaps: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class AudioChunk:
    index: int
    decode_start: float
    duration: float
    path: Path
    content_start: float
    content_end: float
    actual_samples: int | None = None
    sample_rate: int = PCM_SAMPLE_RATE
    expected_duration: float | None = None

    @property
    def start(self) -> float:
        """Compatibility alias for the decoded audio's absolute timestamp."""
        return self.decode_start


def measure_pyav_decode(source: Path, output_rate: int = PCM_SAMPLE_RATE) -> DecodeDiagnostics:
    """Measure actual decoded PCM rather than trusting container metadata."""
    import av

    assert_supported(source)
    with av.open(str(source), mode="r") as container:
        stream = next((item for item in container.streams if item.type == "audio"), None)
        if stream is None:
            raise MediaError("В медиафайле нет аудиодорожки.", "media_open")
        container_duration = float(container.duration / av.time_base) if container.duration else None
        stream_duration = float(stream.duration * stream.time_base) if stream.duration is not None and stream.time_base else None
        resampler = av.AudioResampler(format="s16", layout="mono", rate=output_rate)
        frames = source_samples = output_samples = 0
        first_frame_time = last_frame_time = None
        for frame in container.decode(stream):
            frames += 1; source_samples += frame.samples
            frame_start = float(frame.time) if frame.time is not None else None
            frame_end = frame_start + frame.samples / frame.sample_rate if frame_start is not None else None
            first_frame_time = frame_start if first_frame_time is None else first_frame_time
            last_frame_time = frame_end if frame_end is not None else last_frame_time
            output_samples += sum(converted.samples for converted in resampler.resample(frame))
        output_samples += sum(converted.samples for converted in resampler.resample(None))
    return DecodeDiagnostics(container_duration, stream_duration, stream.index, stream.rate, frames, source_samples,
                             output_samples, output_rate, output_samples / output_rate, first_frame_time, last_frame_time)


def probe_audio_metadata(source: Path, output_rate: int = PCM_SAMPLE_RATE) -> DecodeDiagnostics:
    """Read stream metadata without a second full decode before chunked ASR."""
    import av

    assert_supported(source)
    with av.open(str(source), mode="r") as container:
        stream = next((item for item in container.streams if item.type == "audio"), None)
        if stream is None:
            raise MediaError("В медиафайле нет аудиодорожки.", "media_open")
        container_duration = float(container.duration / av.time_base) if container.duration else None
        stream_duration = float(stream.duration * stream.time_base) if stream.duration is not None and stream.time_base else None
    estimated_duration = stream_duration or container_duration or 0.0
    return DecodeDiagnostics(container_duration, stream_duration, stream.index, stream.rate, 0, 0, 0, output_rate,
                             estimated_duration, None, None)


def logical_coverage(intervals: Iterable[tuple[float, float]], duration: float, tolerance: float = 0.05) -> Coverage:
    """Return the union of owned source intervals; overlap never inflates coverage."""
    cursor, covered, gaps = 0.0, 0.0, []
    for start, end in sorted((max(0.0, start), min(duration, end)) for start, end in intervals if end > start):
        if start > cursor + tolerance:
            gaps.append((cursor, start))
        if end > cursor:
            covered += end - max(cursor, start)
            cursor = end
    if cursor < duration - tolerance:
        gaps.append((cursor, duration))
    return Coverage(min(duration, covered), tuple(gaps))


def assert_supported(path: Path) -> None:
    if not path.is_file():
        raise MediaError("Файл не существует или недоступен.", "media_missing")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise MediaError(f"Неподдерживаемый формат: {path.suffix or 'без расширения'}", "media_unsupported")


def configure_ffmpeg_directory(directory: str | Path | None) -> None:
    """Configure a process-local developer or deployment FFmpeg directory."""
    global _configured_ffmpeg_directory
    _configured_ffmpeg_directory = Path(directory).expanduser() if directory else None


def _binary_name(name: str) -> str:
    return f"{name}.exe" if os.name == "nt" else name


def _bundled_ffmpeg_directories() -> tuple[Path, ...]:
    roots: list[Path] = []
    extraction_root = getattr(sys, "_MEIPASS", None)
    if extraction_root:
        roots.append(Path(extraction_root) / "ffmpeg" / "bin")
    roots.append(Path(sys.executable).resolve().parent / "ffmpeg" / "bin")
    return tuple(dict.fromkeys(roots))


def _configured_ffmpeg_directories() -> tuple[Path, ...]:
    configured = _configured_ffmpeg_directory or (Path(os.environ[FFMPEG_DIRECTORY_ENV]).expanduser()
                                                   if os.environ.get(FFMPEG_DIRECTORY_ENV) else None)
    return (configured,) if configured else ()


def resolve_ffmpeg_binary(name: str) -> Path | None:
    """Resolve a binary as bundled, configured, then inherited PATH, in that order."""
    binary = _binary_name(name)
    for directory in (*_bundled_ffmpeg_directories(), *_configured_ffmpeg_directories()):
        candidate = directory / binary
        if candidate.is_file():
            return candidate
    inherited = shutil.which(binary) or shutil.which(name)
    return Path(inherited) if inherited else None


def ffmpeg_available() -> bool:
    return resolve_ffmpeg_binary("ffmpeg") is not None and resolve_ffmpeg_binary("ffprobe") is not None


def ffmpeg_resolution() -> dict[str, str | None]:
    """Diagnostic view of the effective process-local binary resolution."""
    return {name: str(path) if (path := resolve_ffmpeg_binary(name)) else None for name in ("ffmpeg", "ffprobe")}


def get_duration(path: Path) -> float:
    assert_supported(path)
    try:
        return _pyav_duration(path)
    except Exception as pyav_error:
        logging.getLogger("transcripta").warning("PyAV duration probe failed for %s: %s", path, pyav_error)
    if not ffmpeg_available():
        raise MediaError("Не удалось открыть медиафайл. Формат повреждён или не поддерживается.", "media_open")
    return _ffmpeg_duration(path)


def _pyav_duration(path: Path) -> float:
    """Read duration from PyAV metadata without decoding the full media file."""
    import av
    with av.open(str(path), mode="r") as container:
        if container.duration is not None and container.duration > 0:
            return float(container.duration / av.time_base)
        for stream in container.streams:
            if stream.type == "audio" and stream.duration is not None and stream.time_base:
                duration = float(stream.duration * stream.time_base)
                if duration > 0:
                    return duration
    raise ValueError("media duration is missing")


def _ffmpeg_duration(path: Path) -> float:
    """Optional external fallback for unusual media; never the normal workflow."""
    ffprobe = resolve_ffmpeg_binary("ffprobe")
    assert ffprobe is not None
    command = [str(ffprobe), "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if completed.returncode:
        raise MediaError("Не удалось прочитать длительность файла. Возможно, файл повреждён.")
    try:
        duration = float(json.loads(completed.stdout)["format"]["duration"])
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as error:
        raise MediaError("FFprobe вернул некорректные метаданные.") from error
    if duration <= 0:
        raise MediaError("Не удалось открыть медиафайл. Формат повреждён или не поддерживается.", "media_open")
    return duration


def format_duration(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    hours, remaining = divmod(total, 3600)
    minutes, seconds = divmod(remaining, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def chunk_count(duration: float, chunk_seconds: int) -> int:
    if duration <= 0 or chunk_seconds <= 0:
        raise ValueError("duration and chunk_seconds must be positive")
    return max(1, int((duration + chunk_seconds - 0.001) // chunk_seconds))


def stream_chunks(source: Path, work_dir: Path, duration: float, chunk_seconds: int, start_index: int = 0,
                  overlap_seconds: int = 0, start_at_seconds: float | None = None) -> Iterator[AudioChunk]:
    """Decode one bounded WAV at a time with optional left context and no RAM accumulation.

    `content_start`/`content_end` identify the non-overlapping ownership range. The ASR may
    read left context, but only transcript material owned by that range is committed.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    index = start_index
    content_start = start_at_seconds if start_at_seconds is not None else start_index * chunk_seconds
    while content_start < duration:
        content_end = min(duration, content_start + chunk_seconds)
        decode_start = max(0.0, content_start - max(0, overlap_seconds))
        chunk_duration = content_end - decode_start
        output = work_dir / f"chunk_{index:06d}.wav"
        try:
            written = _write_pyav_wav_chunk(source, output, decode_start, content_end)
        except Exception as pyav_error:
            logging.getLogger("transcripta").warning("PyAV chunk decode failed for %s at %.3f: %s", source, decode_start, pyav_error)
            if not ffmpeg_available():
                raise MediaError("Не удалось открыть медиафайл. Формат повреждён или не поддерживается.", "media_open") from pyav_error
            written = _write_ffmpeg_wav_chunk(source, output, decode_start, chunk_duration, content_start)
        actual_duration = written / PCM_SAMPLE_RATE
        if abs(actual_duration - chunk_duration) > CHUNK_DURATION_TOLERANCE_SECONDS:
            output.unlink(missing_ok=True)
            raise MediaError(f"Decoded chunk duration mismatch: expected {chunk_duration:.3f}s, got {actual_duration:.3f}s.", "media_pipeline")
        yield AudioChunk(index=index, decode_start=decode_start, duration=actual_duration, path=output,
                         content_start=content_start, content_end=content_end, actual_samples=written,
                         sample_rate=PCM_SAMPLE_RATE, expected_duration=chunk_duration)
        index += 1
        content_start = content_end


def _s16_mono_bytes(frame) -> bytes:
    """Trim PyAV plane alignment padding: buffer_size is not the PCM sample count."""
    required = frame.samples * frame.format.bytes
    payload = bytes(frame.planes[0])[:required]
    if len(payload) != required:
        raise ValueError("PyAV returned a truncated PCM plane")
    return payload


def _write_pyav_wav_chunk(source: Path, output: Path, decode_start: float, content_end: float) -> int:
    """Decode only a seekable bounded region to mono 16 kHz PCM WAV using PyAV."""
    import av
    output.unlink(missing_ok=True)
    with av.open(str(source), mode="r") as container:
        stream = next((item for item in container.streams if item.type == "audio"), None)
        if stream is None:
            raise ValueError("no audio stream")
        try:
            container.seek(max(0, int(decode_start * av.time_base)), backward=True, any_frame=False)
        except Exception:
            # Some containers cannot seek cleanly; decoding from the beginning remains bounded in memory.
            pass
        resampler = av.AudioResampler(format="s16", layout="mono", rate=PCM_SAMPLE_RATE)
        written = 0
        with wave.open(str(output), "wb") as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(PCM_SAMPLE_RATE)

            def write_converted(converted) -> int:
                """Write only samples in [decode_start, content_end), never frame spillover."""
                converted_start = float(converted.time) if converted.time is not None else decode_start
                first = max(0, ceil((decode_start - converted_start) * PCM_SAMPLE_RATE - 1e-9))
                end = min(converted.samples, ceil((content_end - converted_start) * PCM_SAMPLE_RATE - 1e-9))
                if end <= first:
                    return 0
                pcm = _s16_mono_bytes(converted)
                wav.writeframes(pcm[first * 2:end * 2])
                return end - first

            for frame in container.decode(stream):
                frame_start = float(frame.time) if frame.time is not None else 0.0
                frame_end = frame_start + float(frame.samples / frame.sample_rate)
                if frame_end <= decode_start:
                    continue
                if frame_start >= content_end:
                    break
                for converted in resampler.resample(frame):
                    written += write_converted(converted)
            for converted in resampler.resample(None):
                written += write_converted(converted)
    if written <= 0 or not output.is_file() or output.stat().st_size <= 44:
        raise ValueError("PyAV produced no audio samples")
    return written


def _write_ffmpeg_wav_chunk(source: Path, output: Path, decode_start: float, chunk_duration: float, content_start: float) -> int:
    ffmpeg = resolve_ffmpeg_binary("ffmpeg")
    assert ffmpeg is not None
    command = [str(ffmpeg), "-y", "-v", "error", "-ss", f"{decode_start:.3f}", "-t", f"{chunk_duration:.3f}", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(output)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if completed.returncode or not output.exists() or output.stat().st_size == 0:
        raise MediaError("Не удалось открыть медиафайл. Формат повреждён или не поддерживается.", "media_open")
    with wave.open(str(output), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getframerate() != PCM_SAMPLE_RATE:
            raise MediaError("FFmpeg produced an unexpected PCM format.", "media_pipeline")
        return wav.getnframes()

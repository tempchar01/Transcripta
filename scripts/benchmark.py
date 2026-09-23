from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

from app.audio.media import get_duration
from app.config.settings import APP_DATA_DIR, AppSettings
from app.hardware.gpu import detect_gpu_runtime
from app.hardware.profiles import resolve_profile
from app.jobs.runner import TranscriptionJob
from app.transcription.model_manager import ModelManager


class ProcessSampler:
    """Low-rate, benchmark-only telemetry for the process doing ASR.

    This is intentionally not part of the application runtime: production only
    samples VRAM at safe chunk boundaries and never keeps ``nvidia-smi`` alive.
    """

    def __init__(self, interval_seconds: float = 1.0) -> None:
        self.interval_seconds = interval_seconds
        self.samples: list[dict[str, float | int | None]] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="benchmark-sampler", daemon=True)
        self._last_wall: float | None = None
        self._last_cpu: float | None = None

    @staticmethod
    def _process_cpu_seconds() -> float | None:
        if os.name != "nt":
            return None
        created, exited, kernel, user = (ctypes.c_ulonglong() for _ in range(4))
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            ok = kernel32.GetProcessTimes(kernel32.GetCurrentProcess(), ctypes.byref(created), ctypes.byref(exited),
                                          ctypes.byref(kernel), ctypes.byref(user))
            return (kernel.value + user.value) / 10_000_000 if ok else None
        except OSError:
            return None

    @staticmethod
    def _working_set_mb() -> float | None:
        if os.name != "nt":
            return None
        class Counters(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t)]
        counters = Counters(); counters.cb = ctypes.sizeof(counters)
        try:
            kernel32, psapi = ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("psapi", use_last_error=True)
            ok = psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
            return round(counters.WorkingSetSize / 1024 / 1024, 1) if ok else None
        except OSError:
            return None

    @staticmethod
    def _os_thread_count() -> int | None:
        """Count native threads too, not only Python's own sampler thread."""
        if os.name != "nt":
            return None
        class ThreadEntry(ctypes.Structure):
            _fields_ = [("dwSize", ctypes.c_ulong), ("cntUsage", ctypes.c_ulong),
                        ("th32ThreadID", ctypes.c_ulong), ("th32OwnerProcessID", ctypes.c_ulong),
                        ("tpBasePri", ctypes.c_long), ("tpDeltaPri", ctypes.c_long), ("dwFlags", ctypes.c_ulong)]
        invalid_handle = ctypes.c_void_p(-1).value
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        snapshot = kernel32.CreateToolhelp32Snapshot(0x00000004, 0)
        if snapshot == invalid_handle:
            return None
        try:
            entry = ThreadEntry(); entry.dwSize = ctypes.sizeof(entry); count = 0
            more = kernel32.Thread32First(snapshot, ctypes.byref(entry))
            while more:
                count += entry.th32OwnerProcessID == os.getpid()
                entry.dwSize = ctypes.sizeof(entry)
                more = kernel32.Thread32Next(snapshot, ctypes.byref(entry))
            return count
        finally:
            kernel32.CloseHandle(snapshot)

    @staticmethod
    def _gpu_sample() -> tuple[int | None, int | None]:
        if not shutil.which("nvidia-smi"):
            return None, None
        try:
            import subprocess
            completed = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"],
                                       capture_output=True, text=True, check=False, timeout=3,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            fields = completed.stdout.strip().splitlines()[0].split(",") if completed.returncode == 0 and completed.stdout.strip() else []
            return (int(fields[0].strip()), int(fields[1].strip())) if len(fields) == 2 else (None, None)
        except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
            return None, None

    def _sample(self) -> None:
        now, cpu = time.monotonic(), self._process_cpu_seconds()
        cpu_percent = None
        if self._last_wall is not None and self._last_cpu is not None and cpu is not None:
            elapsed = now - self._last_wall
            # Normalized to all logical processors, matching Task Manager's process percentage.
            cpu_percent = round(100 * (cpu - self._last_cpu) / max(elapsed, .001) / max(1, os.cpu_count() or 1), 1)
        self._last_wall, self._last_cpu = now, cpu
        gpu_percent, vram_mb = self._gpu_sample()
        self.samples.append({"cpu_percent": cpu_percent, "gpu_percent": gpu_percent, "vram_mb": vram_mb,
                             "ram_mb": self._working_set_mb(), "threads": self._os_thread_count()})

    def _run(self) -> None:
        while not self._stop.is_set():
            self._sample()
            self._stop.wait(self.interval_seconds)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> dict[str, float | int | None]:
        self._stop.set(); self._thread.join(timeout=5)
        def summary(key: str) -> tuple[float | int | None, float | int | None]:
            values = [item[key] for item in self.samples if item[key] is not None]
            return (round(sum(values) / len(values), 1), max(values)) if values else (None, None)
        cpu_avg, cpu_peak = summary("cpu_percent"); gpu_avg, gpu_peak = summary("gpu_percent")
        _ram_avg, ram_peak = summary("ram_mb"); _vram_avg, vram_peak = summary("vram_mb")
        _threads_avg, threads_peak = summary("threads")
        return {"sample_interval_seconds": self.interval_seconds, "sample_count": len(self.samples),
                "cpu_process_percent_average": cpu_avg, "cpu_process_percent_peak": cpu_peak,
                "gpu_percent_average": gpu_avg, "gpu_percent_peak": gpu_peak,
                "ram_mb_peak": ram_peak, "vram_mb_peak": vram_peak,
                "process_threads_peak": threads_peak}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Run one real local Transcripta ASR benchmark.")
    parser.add_argument("audio", type=Path)
    parser.add_argument("--model", choices=("auto", "small", "medium", "large"), default="auto")
    parser.add_argument("--profile", choices=("eco", "balanced", "maximum_speed", "auto", "fast", "memory_saver", "quality", "cpu"), default="balanced")
    parser.add_argument("--vram-class", choices=("6", "8", "12", "16"), help="Policy simulation only; does not emulate physical OOM.")
    parser.add_argument("--app-data", type=Path, help="Use an isolated job/checkpoint directory; model cache remains local.")
    parser.add_argument("--allow-model-download", action="store_true", help="Explicitly permit a missing model download.")
    arguments = parser.parse_args()

    settings = AppSettings()
    settings.recognition.model = arguments.model
    settings.recognition.performance_profile = arguments.profile
    settings.recognition.vram_limit_mb = int(arguments.vram_class) * 1024 if arguments.vram_class else None
    settings.export.txt = settings.export.docx = settings.export.srt = settings.export.json = False
    sampler = ProcessSampler()
    benchmark_started = time.monotonic()
    sampler.start()
    result = None
    try:
      with tempfile.TemporaryDirectory(prefix="transcripta-benchmark-") as temporary:
        settings.export.output_dir = temporary
        try:
            duration = get_duration(arguments.audio)
            job_data = arguments.app_data or APP_DATA_DIR
            if arguments.app_data:
                # A benchmark may not mutate an interactive user's checkpoint directory.
                job_data.mkdir(parents=True, exist_ok=True)
                job = TranscriptionJob(arguments.audio, duration, settings, job_data, arguments.allow_model_download,
                                       on_warning=lambda message: print(f"WARNING: {message}", file=sys.stderr),
                                       model_manager=ModelManager(APP_DATA_DIR / "models"))
            else:
                job = TranscriptionJob(arguments.audio, duration, settings, job_data, arguments.allow_model_download,
                                   on_warning=lambda message: print(f"WARNING: {message}", file=sys.stderr))
            result = job.run()
        except Exception as error:
            print(json.dumps({"error": str(error), "gpu_runtime": detect_gpu_runtime().to_dict()}, ensure_ascii=False, indent=2))
            return 1
    finally:
        telemetry = sampler.stop()
    assert result is not None
    report = {
        "gpu_runtime": detect_gpu_runtime().to_dict(), "selected_profile": result.hardware_profile.to_dict(),
        "audio_duration_seconds": duration, "processing_seconds": result.processing_seconds,
        "realtime_factor": result.processing_seconds / duration, "model_load_seconds": result.model_load_seconds,
        "peak_ram_mb": result.peak_ram_mb, "peak_vram_mb_sampled": result.peak_vram_mb,
        "segments": len(result.transcript.segments), "output_characters": sum(len(item.text) for item in result.transcript.segments),
        "actual_device": result.device, "gpu_inference_succeeded": result.gpu_inference_succeeded,
        "wall_clock_seconds": round(time.monotonic() - benchmark_started, 3),
        "wall_clock_realtime_factor": round((time.monotonic() - benchmark_started) / duration, 4),
        "telemetry": telemetry,
        "asr_workers": result.hardware_profile.max_workers,
        "model_load_count": result.model_load_count,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

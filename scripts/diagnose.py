from __future__ import annotations

import importlib.metadata
import json
import argparse
import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import sys

from app.hardware.gpu import detect_gpu_runtime, system_summary
from app.hardware.nvidia_runtime import activate_nvidia_runtime_paths
from app.hardware.profiles import resolve_profile


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def module_imported(name: str) -> dict[str, str | bool]:
    try:
        __import__(name)
        return {"available": True, "detail": "imported"}
    except Exception as error:
        return {"available": False, "detail": str(error)}


def binary_version(binary: str) -> str | None:
    if not shutil.which(binary):
        return None
    try:
        output = subprocess.run([binary, "-version"], capture_output=True, text=True, check=False, timeout=5).stdout
        return output.splitlines()[0] if output else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def dll_probe(name: str) -> dict[str, str | bool]:
    if os.name != "nt":
        return {"available": False, "detail": "Windows DLL probe is not applicable."}
    try:
        ctypes.WinDLL(name)
        return {"available": True, "detail": "loaded"}
    except OSError as error:
        return {"available": False, "detail": str(error)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Transcripta dependencies and optionally run a CUDA-only ASR smoke test.")
    parser.add_argument("--smoke-audio", type=str, help="Real speech audio for a CUDA-only test.")
    parser.add_argument("--smoke-model", choices=("tiny", "small"), default="tiny")
    parser.add_argument("--smoke-compute", choices=("float16", "int8_float16"), action="append")
    parser.add_argument("--allow-model-download", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    runtime_paths = activate_nvidia_runtime_paths()
    runtime = detect_gpu_runtime()
    profile = resolve_profile(runtime)
    report = {
        **system_summary(), "pyside6": package_version("PySide6"), "faster_whisper": package_version("faster-whisper"),
        "ctranslate2": package_version("ctranslate2"), "ffmpeg": binary_version("ffmpeg"), "ffprobe": binary_version("ffprobe"),
        "python_support": {
            "primary_baseline": "3.14",
            "compatibility_baseline": "3.12",
            "current_supported": sys.version_info[:2] in ((3, 14), (3, 12)),
        },
        "gpu_runtime": runtime.to_dict(), "recommended_profile": profile.to_dict(),
        "gpu_inference_confirmed": False,
        "python_modules": {
            "ctranslate2": module_imported("ctranslate2"),
            "faster_whisper": module_imported("faster_whisper"),
            "av": module_imported("av"),
        },
        "whisper_model_construction": {"attempted": False, "detail": "Pass --smoke-audio to construct and use a CUDA model."},
        "note": "Only a successful benchmark/inference marks GPU inference as confirmed.",
        "cuda_dlls": {
            "cublas64_12.dll": dll_probe("cublas64_12.dll"),
            "cublasLt64_12.dll": dll_probe("cublasLt64_12.dll"),
            "cudnn64_8.dll": dll_probe("cudnn64_8.dll"),
            "cudnn64_9.dll": dll_probe("cudnn64_9.dll"),
        },
        "nvidia_runtime_paths": {
            "discovered": [str(path) for path in runtime_paths.discovered],
            "activated": [str(path) for path in runtime_paths.activated],
            "missing_packages": list(runtime_paths.missing_packages),
        },
    }
    if args.smoke_audio:
        from scripts.gpu_smoke import run_smoke
        smoke_results = [run_smoke(Path(args.smoke_audio), args.smoke_model, compute, args.allow_model_download)
                         for compute in (args.smoke_compute or ["float16", "int8_float16"])]
        report["gpu_smoke"] = smoke_results
        report["whisper_model_construction"] = {"attempted": True, "passed": all(item.get("model_loaded_on_cuda") for item in smoke_results)}
        report["gpu_inference_confirmed"] = all(item.get("gpu_inference_passed") for item in smoke_results)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not args.smoke_audio or report["gpu_inference_confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

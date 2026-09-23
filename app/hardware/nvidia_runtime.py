from __future__ import annotations

import importlib.metadata
import logging
import os
from dataclasses import dataclass
from pathlib import Path


_PACKAGE_LAYOUTS = {
    "nvidia-cublas-cu12": Path("nvidia") / "cublas" / "bin",
    "nvidia-cudnn-cu12": Path("nvidia") / "cudnn" / "bin",
}
_CTRANSLATE2_RUNTIME_PACKAGE = "ctranslate2"
_CTRANSLATE2_RUNTIME_DIRECTORY = Path("ctranslate2")
_DLL_DIRECTORY_HANDLES: list[object] = []
_ACTIVE_PATHS: set[Path] = set()
_PROCESS_PATHS: set[Path] = set()


@dataclass(frozen=True, slots=True)
class NvidiaRuntimePaths:
    discovered: tuple[Path, ...]
    activated: tuple[Path, ...]
    missing_packages: tuple[str, ...]


def discover_nvidia_runtime_paths() -> tuple[tuple[Path, ...], tuple[str, ...]]:
    """Discover package-local NVIDIA DLL directories without importing CTranslate2.

    CTranslate2 4.8.2 wheels can carry cuDNN 9 beside ``ctranslate2.dll``.  That
    directory is a valid cuDNN runtime source when the optional standalone
    ``nvidia-cudnn-cu12`` distribution is absent.
    """
    found: list[Path] = []
    missing: list[str] = []
    for package, relative_path in _PACKAGE_LAYOUTS.items():
        try:
            distribution = importlib.metadata.distribution(package)
        except importlib.metadata.PackageNotFoundError:
            missing.append(package)
            continue
        directory = Path(distribution.locate_file(relative_path))
        if directory.is_dir():
            found.append(directory.resolve())
        else:
            missing.append(package)
    try:
        ctranslate2 = importlib.metadata.distribution(_CTRANSLATE2_RUNTIME_PACKAGE)
    except importlib.metadata.PackageNotFoundError:
        missing.append(_CTRANSLATE2_RUNTIME_PACKAGE)
    else:
        directory = Path(ctranslate2.locate_file(_CTRANSLATE2_RUNTIME_DIRECTORY))
        if directory.is_dir() and any(directory.glob("cudnn64_*.dll")):
            found.append(directory.resolve())
        else:
            missing.append("ctranslate2 bundled cuDNN")
    return tuple(dict.fromkeys(found)), tuple(missing)


def activate_nvidia_runtime_paths(logger: logging.Logger | None = None) -> NvidiaRuntimePaths:
    """Add package-local DLL locations to this process, never to user/system PATH.

    The returned handles are held at module scope because Windows removes a directory from
    the DLL search list when its `os.add_dll_directory` handle is closed or collected.
    """
    logger = logger or logging.getLogger("transcripta")
    discovered, missing = discover_nvidia_runtime_paths()
    activated: list[Path] = []
    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        return NvidiaRuntimePaths(discovered, (), missing)
    for directory in discovered:
        if directory in _ACTIVE_PATHS:
            activated.append(directory)
            continue
        try:
            handle = os.add_dll_directory(str(directory))
        except OSError as error:
            logger.warning("Unable to add NVIDIA runtime DLL directory %s: %s", directory, error)
            continue
        _DLL_DIRECTORY_HANDLES.append(handle)
        _ACTIVE_PATHS.add(directory)
        activated.append(directory)
        logger.info("Activated NVIDIA runtime DLL directory: %s", directory)
        # CTranslate2 4.8.2 also resolves cuBLAS by name at runtime.  In practice
        # that loader consults the process PATH even after AddDllDirectory.  This is
        # deliberately process-local: it is inherited only by child processes that
        # this Python process starts and never persists to the user or system PATH.
        if directory not in _PROCESS_PATHS:
            current = os.environ.get("PATH", "")
            entries = [Path(item) for item in current.split(os.pathsep) if item]
            if directory not in entries:
                os.environ["PATH"] = str(directory) + (os.pathsep + current if current else "")
                logger.info("Added NVIDIA runtime directory to the current process PATH: %s", directory)
            _PROCESS_PATHS.add(directory)
    if missing:
        logger.info("NVIDIA runtime packages not found: %s", ", ".join(missing))
    return NvidiaRuntimePaths(discovered, tuple(activated), missing)

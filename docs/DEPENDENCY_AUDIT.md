# Dependency audit

## Runtime application dependencies

| Component | Purpose | Release treatment |
| --- | --- | --- |
| Python 3.14 | confirmed primary runtime | bundle interpreter in release |
| PySide6 | native desktop UI | bundle Qt plugins explicitly |
| faster-whisper 1.1.1 | transcription API | bundle Python package |
| CTranslate2 4.8.2 | CPU/CUDA inference | bundle native binaries and test on clean Windows |
| nvidia-cublas-cu12 | CUDA 12 cuBLAS DLLs | Windows GPU runtime dependency; auto-discovered in-process |
| cuDNN 9 | CTranslate2 package-local runtime | discover and test in-process |
| PyAV | media decoding support | bundle its native libraries explicitly |
| python-docx | DOCX export | Python-only dependency |
| FFmpeg/FFprobe | deterministic probing and chunk extraction | bundle provenance-checked binaries; never ask user to alter PATH |

The NVIDIA driver is an external prerequisite. CUDA Toolkit is not. Models are optional data downloaded only after user approval and must be stored outside the application installation directory.

## Review outcome

No unused runtime package was added by the UI/localization work. PyInstaller, Nuitka, and an installer compiler are intentionally not declared runtime dependencies; they belong to a reproducible release-build environment after the E2E gate.

Before release, generate a lockfile with hashes from the selected CPython 3.14 environment and retain the exact FFmpeg source/version and NVIDIA package versions in the build manifest.

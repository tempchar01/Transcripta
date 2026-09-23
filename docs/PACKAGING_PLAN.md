# Packaging plan

The release must not require an end user to install Python, pip, FFmpeg, or the full CUDA Toolkit. This is a plan, not an installer implementation.

## Runtime inventory

- Python application and PySide6/Qt plugins;
- faster-whisper, CTranslate2 and an initially empty controlled ASR model cache;
- PyAV libraries for direct media decoding;
- optional FFmpeg/FFprobe fallback at `ffmpeg/bin` beside the packaged executable;
- Visual C++ runtime;
- NVIDIA driver plus the exact CUDA/cuBLAS/cuDNN runtime that passes `scripts.gpu_smoke`.

PyAV is the primary duration and bounded WAV chunk backend, so standard transcription does not depend on a system `ffmpeg.exe`. Production may bundle a provenance-checked FFmpeg build for difficult media fallbacks. `app.audio.media` resolves that optional bundled location before optional local configuration and inherited PATH.

## Candidate packagers

| Option | Strengths | Risks / work |
| --- | --- | --- |
| PyInstaller | Mature Windows one-folder builds, PySide6 hooks, familiar installer ecosystem. | Collect Qt plugins, PyAV binaries, CTranslate2 and CUDA DLLs explicitly; one-file startup and AV false positives are poorer. |
| Nuitka | Native compilation, often better startup, can package Qt. | Longer build/debug cycle; CUDA/Qt/PyAV data collection still needs explicit validation. |
| Briefcase | Python-native application workflow. | Less mature for this GPU/DLL-heavy stack; not the preferred first validation path. |

## Recommended validation order

1. After the real PyAV E2E validator passes, build a PyInstaller **one-folder** prototype; do not start with one-file.
2. Collect optional `ffmpeg/bin`, PySide6 plugins, CTranslate2 and package-local NVIDIA runtime DLL directories, then run `diagnose`, CUDA-only smoke, a short Russian GUI transcription, and exports from a clean Windows VM.
3. Inventory all DLLs with license/provenance, especially NVIDIA components and FFmpeg.
4. Add an installer only after the one-folder result is reproducible.

## Size and installer gates

Run `python -m scripts.size_audit <distribution-dir>` after each build. It reports total size, top-level package groups, and byte-identical duplicate content; it does not delete anything automatically.

The first installer prototype is deliberately deferred until the real E2E pipeline passes. It should support Russian/English installer strings, bundle its preferred runtime layout, create no automatic large-model download, and store settings/models/logs/exports in `%LOCALAPPDATA%\\Transcripta` rather than Program Files.

No option is selected for release yet. PyInstaller one-folder is the lowest-risk experiment, not a production commitment.

## First-use model policy

Do not embed `large-v3` in the initial installer: it would add several GB before one-folder and installer validation exist. The initial small installer creates a controlled model cache and downloads the AUTO-selected configured Systran faster-whisper model only after the user confirms it. A future web installer and a full offline installer are separate packaging decisions.

## Brand integration contract

`app/ui/assets.py` resolves the controlled production icon at `assets/branding/generated/app_icon.ico`. `scripts/extract_branding.py` documents the approved crop from the supplied branding board. Both `packaging/transcripta.spec` and `installer/Transcripta.iss` use that same generated production ICO.

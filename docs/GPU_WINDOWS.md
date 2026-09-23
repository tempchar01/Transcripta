# Windows GPU runtime

## Status of the development machine

Locally reproduced runtime: Python 3.14.3, faster-whisper 1.1.1, CTranslate2 4.8.2, RTX 5060 Ti, CUDA, cuDNN 9, and cuBLAS from `nvidia-cublas-cu12`. A real `tiny`/`float16` Russian CUDA inference passed in a new process without a manual PATH edit (RTF 0.4564; sampled peak VRAM 1,038 MB). The project bootstrap creates a separate `.venv` when needed, but the runtime facts below were verified in the installed Python 3.14 environment.

## Pinned software

| Layer | Version / requirement |
| --- | --- |
| Python | CPython 3.14 x64 primary; 3.12 remains supported when dependencies install |
| faster-whisper | 1.1.1 |
| CTranslate2 | 4.8.2 |
| GPU | NVIDIA driver supporting CUDA 12.x |
| Windows runtime | Microsoft Visual C++ Redistributable x64 |

## Confirmed CUDA and cuDNN runtime

There is an upstream documentation conflict: CTranslate2 4.8 documentation mentions cuDNN 8, while faster-whisper documents CUDA 12/cuDNN 9 for its current CTranslate2 path. The supplied real runtime evidence resolves this for Transcripta's confirmed configuration: **cuDNN 9 works with CTranslate2 4.8.2 on this RTX 5060 Ti**.

The acceptance procedure is therefore:

1. Install the NVIDIA driver; do not require the full CUDA Toolkit.
2. Install runtime dependencies including `nvidia-cublas-cu12`. The validated CTranslate2 4.8.2 wheel includes `cudnn64_9.dll`; a separate CUDA Toolkit or cuDNN installation is not required for this runtime.
3. Transcripta discovers `nvidia/cublas/bin`, optional `nvidia/cudnn/bin`, and the CTranslate2 directory containing cuDNN, then calls `os.add_dll_directory()` before importing CTranslate2. CTranslate2 4.8.2 additionally resolves cuBLAS through the current process `PATH`, so Transcripta prepends the discovered directories to that process only. It does not write or persist the user or system `PATH`.
4. Run `python -m scripts.diagnose`: cublas/cudnn DLL probes and `get_supported_compute_types("cuda")` must succeed.
5. Run CUDA-only tests; neither is permitted to fall back to CPU:

```powershell
python -m scripts.gpu_smoke .\samples\russian-speech.wav --model tiny --compute float16 --allow-model-download
python -m scripts.gpu_smoke .\samples\russian-speech.wav --model tiny --compute int8_float16 --allow-model-download
```

The clean-start reproduction is still required in this workspace before this configuration is promoted from externally confirmed to locally reproduced.

## What each result means

| Signal | Meaning |
| --- | --- |
| GPU detected | `nvidia-smi` sees hardware and driver. |
| CUDA libraries available | expected cuBLAS/cuDNN DLLs load in the process. |
| CTranslate2 CUDA available | `get_supported_compute_types("cuda")` returns nonempty. |
| Model loaded on CUDA | `WhisperModel(... device="cuda")` constructed. |
| GPU inference passed | generator iterated over real speech with no CPU fallback. |

The last row is the only proof of a working ASR GPU pipeline.

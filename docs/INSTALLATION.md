# Установка

## Python

Используйте CPython 3.14 x64: это основной подтверждённый runtime Transcripta. CPython 3.12 не запрещён, но поддерживается лишь при успешной установке pinned зависимостей и прохождении диагностики на конкретной машине.

```powershell
.\scripts\bootstrap_windows.ps1
```

Bootstrap предпочитает Python 3.14, затем допускает 3.12, и не удаляет или не переиспользует молча виртуальное окружение другой версии. Если Python 3.14 отсутствует и доступен `winget`, передайте явный `-InstallPython`; иначе установите CPython через официальный installer и запустите скрипт снова.

## Media runtime

PyAV is the primary runtime for duration probing and bounded 16 kHz WAV chunk extraction. A normal developer or end user does **not** need `ffmpeg.exe`, `ffprobe.exe`, or a PATH change for supported media. External FFmpeg remains an optional fallback for unusual container failures; Transcripta resolves it from bundled `ffmpeg/bin`, `TRANSCRIPTA_FFMPEG_DIR`, then inherited `PATH`.

```powershell
ffmpeg -version
ffprobe -version
```

```powershell
python -m scripts.e2e_validate .\samples\russian.ogg --chunk-seconds 45
```

## GPU

Проверьте драйвер:

```powershell
nvidia-smi
```

`nvidia-smi` alone does not prove that Python/CTranslate2 can load CUDA. `requirements.txt` installs `nvidia-cublas-cu12`; the validated CTranslate2 4.8.2 wheel carries `cudnn64_9.dll`. Before importing CTranslate2, Transcripta discovers those package-local directories and activates them with `os.add_dll_directory()` for its own process. It never changes the user or system `PATH`, and the CUDA Toolkit is not a prerequisite. Use [GPU_WINDOWS.md](GPU_WINDOWS.md) and `python -m scripts.diagnose`; they probe DLLs, CTranslate2 compute types, model construction and optional real CUDA-only inference.

Запуск:

```powershell
python -m app.main
```

## Модели распознавания

Installer не включает многогигабайтные модели. При первой транскрибации Transcripta до запуска ASR показывает выбранную AUTO-политикой модель, ориентировочный размер и controlled cache. После явного выбора **«Скачать и продолжить»** модель загружается по HTTPS в `%LOCALAPPDATA%\Transcripta\models`, проверяется и исходная задача запускается автоматически. Для последующих транскрибаций интернет не требуется.

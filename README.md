# Transcripta

**Transcripta 1.0.0** is a local Windows application for transcribing audio and video. It is designed for private, offline work: media is processed on your computer and is not sent to a transcription API.

## Highlights

- Windows x64 desktop application with NVIDIA CUDA acceleration when a compatible GPU is available;
- local faster-whisper transcription, with `large-v3` selected automatically on suitable 12 GB+ VRAM systems and a `medium` fallback for lower-memory hardware;
- **Eco**, **Balanced**, and **Maximum Speed** performance profiles;
- drag and drop or file selection for MP3, WAV, M4A, FLAC, OGG, OPUS, MP4, MKV, MOV, and WebM;
- Russian and English interface languages;
- Graphite and Pearl themes;
- DOCX export with duplicate-safe filenames;
- explicit, resumable model download and offline recognition after a model is saved locally.

## Privacy

Transcripta performs transcription and DOCX export locally. The only network action is an explicitly confirmed download of a recognition model. Models, settings, logs, and exported documents are stored in the user's local Transcripta data folder; no telemetry or cloud transcription service is used.

## Installation

1. Download the latest `Transcripta-1.0.0-Windows-x64-Setup.exe` from the [Releases](../../releases) page.
2. Run the installer and launch **Transcripta** from the Start menu.
3. Add an audio or video file by dragging it into the window or choosing a file.
4. On the first transcription, confirm the one-time download of the recommended local model. Later transcriptions with that model work offline.

## System requirements

- Windows 10 or Windows 11, x64;
- enough free disk space for the application, source media, DOCX exports, and the chosen local model;
- an NVIDIA GPU with a current driver is recommended for CUDA acceleration;
- 12 GB or more GPU VRAM is recommended when using the automatic `large-v3` policy. Lower-memory systems use the application's supported fallback policy.

The full CUDA Toolkit is not required for the packaged application.

## Screenshots

Screenshots will be added here before public distribution:

| Graphite | Pearl |
| --- | --- |
| _Graphite workspace screenshot_ | _Pearl workspace screenshot_ |

## Documentation

- [Installation](docs/INSTALLATION.md)
- [GPU on Windows](docs/GPU_WINDOWS.md)
- [Models](docs/MODELS.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Development](docs/DEVELOPMENT.md)

## Author and support

Created by **Maksim Pershikov**.

- Email: [tempchar1@outlook.com](mailto:tempchar1@outlook.com)
- Support: [https://app.lava.top/tempchar](https://app.lava.top/tempchar)

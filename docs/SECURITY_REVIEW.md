# Security review — source-level, 2026-09-06

This is a source review, not a penetration test or a clean-machine release sign-off.

## Confirmed controls

- FFmpeg, FFprobe, NVIDIA queries and diagnostics use argument lists with `shell=False` (the subprocess default); media paths are passed as one argument, so shell metacharacters do not become commands.
- Application configuration and checkpoints use write-then-replace, reducing corruption on interruption.
- Models require a visible, explicit download confirmation; local inference does not upload source media.
- CUDA DLL directories are discovered from installed package locations and registered only for the current process. The user’s system PATH is not altered.

## Risks to keep visible

1. `TRANSCRIPTA_FFMPEG_DIR` is a developer/operator override and can point to an arbitrary executable. Production releases must prefer their signed/bundled FFmpeg and should omit this override from end-user documentation.
2. The process-local PATH fallback needed by the CTranslate2 loader means DLL resolution still deserves a clean-machine test with the exact bundled directory order.
3. Model download uses the upstream model mechanism. Release engineering must pin model revision/provenance before claiming supply-chain completeness.
4. Logs and exports may contain source filenames and transcribed sensitive content. Store them under per-user data directories; document retention/deletion in the eventual product privacy page.

No high-severity source finding was identified in the reviewed subprocess, settings, runtime-discovery, and export paths. Full packaging validation remains required.

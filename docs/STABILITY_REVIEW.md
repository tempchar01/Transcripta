# Stability review

The runner uses bounded chunks, checkpoints, pause/cancel boundaries, atomic settings/checkpoint writes, and a bounded GPU OOM downgrade path. The UI keeps inference in a worker `QThread`, so normal progress updates do not block the window.

Known validation gap: the current environment has no usable FFmpeg/FFprobe binaries, so the real decode → chunk → ASR → export GUI/E2E path cannot yet be signed off. This also blocks the long-audio resume test and a packaging prototype.

Operational failure handling remains explicit: missing FFmpeg returns a structured E2E block; missing CUDA falls back through the performance policy; model download never happens silently. A release build should run the full test suite, GPU smoke, E2E validation, long-audio resume, and clean-machine installer flow under its final packaged runtime.

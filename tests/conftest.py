from __future__ import annotations

from array import array
from math import sin, tau
import wave
from pathlib import Path

import pytest


@pytest.fixture
def synthetic_wav(tmp_path: Path) -> Path:
    """A one-second valid silent WAV; no external fixture or network required."""
    path = tmp_path / "synthetic.wav"
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16_000)
        output.writeframes(b"\x00\x00" * 16_000)
    return path


@pytest.fixture
def synthetic_ogg(tmp_path: Path) -> Path:
    """Create a deterministic non-private OGG fixture for GUI media tests."""
    av = pytest.importorskip("av")
    path = tmp_path / "synthetic.ogg"
    samples = array("h", (int(12_000 * sin(tau * 440 * index / 16_000)) for index in range(16_000)))
    container = av.open(str(path), mode="w", format="ogg")
    try:
        stream = container.add_stream("libvorbis", rate=16_000)
        stream.layout = "mono"
        frame = av.AudioFrame(format="s16", layout="mono", samples=len(samples))
        frame.sample_rate = 16_000
        frame.planes[0].update(samples.tobytes())
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    finally:
        container.close()
    assert path.is_file()
    return path

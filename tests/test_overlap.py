from types import SimpleNamespace

from app.audio.media import AudioChunk
from app.core.models import Segment
from app.jobs.runner import TranscriptionJob


def test_overlap_ownership_uses_midpoint_and_removes_left_duplicate():
    chunk = AudioChunk(1, 292.0, 308.0, None, 300.0, 600.0)  # type: ignore[arg-type]
    left_context = Segment(1, 298.0, 299.5, "дубликат")
    owned = Segment(2, 300.2, 301.0, "новый текст")
    assert not TranscriptionJob._is_owned_by_chunk(left_context, chunk)
    assert TranscriptionJob._is_owned_by_chunk(owned, chunk)
    assert TranscriptionJob._is_duplicate(Segment(3, 300.0, 301.0, "Дубликат."), left_context)

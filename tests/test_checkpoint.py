from app.jobs.checkpoint import CheckpointStore, JobCheckpoint
from app.core.models import Segment


def test_checkpoint_round_trip_and_resume_identity(synthetic_wav, tmp_path):
    checkpoint = JobCheckpoint.create(synthetic_wav, 1.0, "ru", "small")
    checkpoint.next_chunk = 1
    checkpoint.segments.append(Segment(1, 0.0, 0.8, "Тест", speaker_id="1"))
    store = CheckpointStore(tmp_path / "job" / "checkpoint.json")
    store.save(checkpoint)

    restored = store.load()
    assert restored is not None
    assert restored.is_for(synthetic_wav, 1.0, "ru", "small")
    assert restored.next_chunk == 1
    assert restored.transcript().segments[0].text == "Тест"
    assert restored.transcript().segments[0].speaker_id == "1"

from app.core.models import Segment, Transcript
from app.transcription.readable import build_readable_transcript, build_speaker_turns, normalize_content


def transcript(segments, language="ru"):
    return Transcript("meeting.mp3", 900.0, language, "large", segments=segments)


def test_segment_boundaries_do_not_become_visible_sentences():
    raw = transcript([Segment(1, 0, 1, "Ну, я думаю,"), Segment(2, 1, 2, "что нам нужно закончить."), Segment(3, 2, 3, "Сегодня.")])
    readable = build_readable_transcript(raw)
    assert readable.plain_text == "Ну, я думаю, что нам нужно закончить. Сегодня."
    assert normalize_content(readable.plain_text) == normalize_content(" ".join(item.text for item in raw.segments))


def test_long_pause_after_sentence_creates_paragraph_without_losing_words():
    raw = transcript([Segment(1, 0, 2, "Первое предложение."), Segment(2, 5, 7, "Второе предложение.")])
    readable = build_readable_transcript(raw)
    assert [item.text for item in readable.paragraphs] == ["Первое предложение.", "Второе предложение."]
    assert normalize_content(" ".join(item.text for item in readable.paragraphs)) == normalize_content(" ".join(item.text for item in raw.segments))


def test_speaker_turns_group_consecutive_speakers_and_change_headings():
    raw = transcript([Segment(1, 600, 601, "Первый фрагмент.", speaker_id="1"), Segment(2, 601, 602, "Второй фрагмент.", speaker_id="1"), Segment(3, 603, 604, "Ответ.", speaker_id="2")])
    turns = build_speaker_turns(raw)
    readable = build_readable_transcript(raw)
    assert [len(turn.segments) for turn in turns] == [2, 1]
    assert readable.plain_text == "Спикер 1\n\nПервый фрагмент. Второй фрагмент.\n\nСпикер 2\n\nОтвет."
    assert readable.paragraphs[0].source_segment_ids == (1, 2)


def test_missing_speaker_id_has_no_speaker_label_and_ten_minute_times_remain_internal():
    raw = transcript([Segment(1, 601.25, 603.75, "Без подписи.")])
    readable = build_readable_transcript(raw)
    assert readable.plain_text == "Без подписи."
    assert readable.paragraphs[0].start == 601.25
    assert raw.segments[0].end == 603.75


def test_unpunctuated_asr_is_split_only_at_a_raw_segment_boundary_without_losing_words():
    raw = transcript([Segment(1, 0, 1, "слово " * 150), Segment(2, 1, 2, "ещё слово")])
    readable = build_readable_transcript(raw)

    assert len(readable.paragraphs) == 2
    assert normalize_content(readable.plain_text) == normalize_content(" ".join(segment.text for segment in raw.segments))

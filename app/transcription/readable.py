"""A lossless presentation layer over raw timestamped ASR segments."""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.models import Segment, Transcript


SENTENCE_END = re.compile(r"[.!?…](?:[\"'»)]*)\s*$")
SOFT_PARAGRAPH_CHARS = 320
HARD_PARAGRAPH_CHARS = 850
LONG_PAUSE_SECONDS = 1.5


def normalize_content(text: str) -> str:
    """Compare content while deliberately ignoring presentation whitespace."""
    return " ".join(text.split())


@dataclass(frozen=True, slots=True)
class SpeakerTurn:
    speaker_id: str | None
    start: float
    end: float
    segments: tuple[Segment, ...]


@dataclass(frozen=True, slots=True)
class ReadableParagraph:
    text: str
    speaker_id: str | None
    start: float
    end: float
    source_segment_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ReadableTranscript:
    paragraphs: tuple[ReadableParagraph, ...]
    language: str

    def speaker_label(self, speaker_id: str) -> str:
        prefix = "Спикер" if self.language == "ru" else "Speaker"
        return f"{prefix} {speaker_id}"

    @property
    def plain_text(self) -> str:
        blocks: list[str] = []
        previous_speaker: str | None | object = object()
        for paragraph in self.paragraphs:
            if paragraph.speaker_id is not None and paragraph.speaker_id != previous_speaker:
                blocks.append(self.speaker_label(paragraph.speaker_id))
            blocks.append(paragraph.text)
            previous_speaker = paragraph.speaker_id
        return "\n\n".join(blocks)


def _meaningful_segments(transcript: Transcript) -> list[Segment]:
    return [segment for segment in sorted(transcript.segments, key=lambda item: (item.start, item.end, item.id))
            if segment.text.strip() and segment.end >= segment.start]


def build_speaker_turns(transcript: Transcript) -> tuple[SpeakerTurn, ...]:
    turns: list[SpeakerTurn] = []
    for segment in _meaningful_segments(transcript):
        if turns and turns[-1].speaker_id == segment.speaker_id:
            previous = turns[-1]
            turns[-1] = SpeakerTurn(previous.speaker_id, previous.start, max(previous.end, segment.end),
                                    (*previous.segments, segment))
        else:
            turns.append(SpeakerTurn(segment.speaker_id, segment.start, segment.end, (segment,)))
    return tuple(turns)


def _paragraphs_for_turn(turn: SpeakerTurn) -> list[ReadableParagraph]:
    paragraphs: list[ReadableParagraph] = []
    current: list[Segment] = []

    def emit() -> None:
        if not current:
            return
        paragraphs.append(ReadableParagraph(" ".join(segment.text.strip() for segment in current), turn.speaker_id,
                                             current[0].start, current[-1].end,
                                             tuple(segment.id for segment in current)))
        current.clear()

    for segment in turn.segments:
        if current:
            previous = current[-1]
            current_text = " ".join(item.text.strip() for item in current)
            pause = max(0.0, segment.start - previous.end)
            ended_sentence = bool(SENTENCE_END.search(previous.text.strip()))
            # Prefer natural sentence endings and meaningful pauses; the hard cap
            # only avoids an unusable multi-hour wall of text when punctuation fails.
            if ended_sentence and (pause >= LONG_PAUSE_SECONDS or len(current_text) >= SOFT_PARAGRAPH_CHARS):
                emit()
            elif len(current_text) >= HARD_PARAGRAPH_CHARS:
                emit()
        current.append(segment)
    emit()
    return paragraphs


def build_readable_transcript(transcript: Transcript) -> ReadableTranscript:
    paragraphs = [paragraph for turn in build_speaker_turns(transcript) for paragraph in _paragraphs_for_turn(turn)]
    readable = ReadableTranscript(tuple(paragraphs), transcript.language)
    raw = normalize_content(" ".join(segment.text.strip() for segment in _meaningful_segments(transcript)))
    rendered = normalize_content(" ".join(paragraph.text for paragraph in readable.paragraphs))
    if raw != rendered:
        raise RuntimeError("Readable transcript integrity check failed: raw ASR content changed.")
    return readable

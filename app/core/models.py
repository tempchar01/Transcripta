from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Word:
    start: float
    end: float
    text: str
    probability: float | None = None


@dataclass(slots=True)
class Segment:
    id: int
    start: float
    end: float
    text: str
    confidence: float | None = None
    words: list[Word] = field(default_factory=list)
    speaker_id: str | None = None

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError("Invalid segment timestamps")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Segment":
        return cls(
            id=int(data["id"]), start=float(data["start"]), end=float(data["end"]),
            text=str(data.get("text", "")), confidence=data.get("confidence"),
            words=[Word(**word) for word in data.get("words", [])], speaker_id=data.get("speaker_id"),
        )


@dataclass(slots=True)
class Transcript:
    source_file: str
    duration: float
    language: str
    model: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    segments: list[Segment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "segments": [segment.to_dict() for segment in self.segments]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transcript":
        return cls(
            source_file=str(data["source_file"]), duration=float(data["duration"]),
            language=str(data.get("language", "auto")), model=str(data.get("model", "unknown")),
            created_at=str(data.get("created_at", datetime.now(timezone.utc).isoformat())),
            segments=[Segment.from_dict(item) for item in data.get("segments", [])],
        )

    @property
    def source_path(self) -> Path:
        return Path(self.source_file)

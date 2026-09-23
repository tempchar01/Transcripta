from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass, field
from pathlib import Path


APP_DATA_DIR = (Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Transcripta"
                if platform.system() == "Windows" else Path.home() / ".transcripta")
DEFAULT_OUTPUT_DIR = APP_DATA_DIR / "output"


@dataclass(slots=True)
class RecognitionSettings:
    model: str = "auto"
    language: str = "ru"
    device: str = "auto"  # Legacy override: auto, cuda, cpu.
    compute_type: str = "auto"  # Legacy override, used only when a profile is not active.
    performance_profile: str = "balanced"  # eco, balanced (default), maximum_speed; old values remain readable.
    vram_limit_mb: int | None = None  # Policy simulation only; never fakes physical VRAM.
    beam_size: int = 5
    vad_filter: bool = True
    word_timestamps: bool = False
    chunk_seconds: int | None = None  # Internal override for integration/endurance runs; production uses HardwareProfile.
    chunk_overlap_seconds: int = 8
    context_mode: str = "previous_chunk_tail"  # none, previous_chunk_tail
    context_chars: int = 224
    condition_on_previous_text: bool = True
    temperature: float = 0.0
    no_speech_threshold: float = 0.6
    compression_ratio_threshold: float = 2.4
    log_prob_threshold: float = -1.0


@dataclass(slots=True)
class ExportSettings:
    output_dir: str = str(DEFAULT_OUTPUT_DIR)


@dataclass(slots=True)
class GeneralSettings:
    """Preferences that affect the shell rather than transcription output."""

    language: str = "system"  # system, ru, en
    theme: str = "system"  # system, light, dark


@dataclass(slots=True)
class AppSettings:
    general: GeneralSettings = field(default_factory=GeneralSettings)
    recognition: RecognitionSettings = field(default_factory=RecognitionSettings)
    export: ExportSettings = field(default_factory=ExportSettings)

    @classmethod
    def from_dict(cls, raw: dict) -> "AppSettings":
        general = GeneralSettings(**{k: v for k, v in raw.get("general", {}).items() if k in GeneralSettings.__dataclass_fields__})
        recognition_values = {k: v for k, v in raw.get("recognition", {}).items() if k in RecognitionSettings.__dataclass_fields__}
        # Existing settings used policy names that are no longer displayed. Keep
        # their intent while ensuring the selector and the effective job agree.
        recognition_values["performance_profile"] = {"auto": "balanced", "memory_saver": "eco",
                                                       "fast": "maximum_speed", "quality": "maximum_speed"}.get(
            recognition_values.get("performance_profile"), recognition_values.get("performance_profile", "balanced"))
        recognition = RecognitionSettings(**recognition_values)
        export = ExportSettings(**{k: v for k, v in raw.get("export", {}).items() if k in ExportSettings.__dataclass_fields__})
        return cls(general=general, recognition=recognition, export=export)

    def to_dict(self) -> dict:
        return asdict(self)


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or APP_DATA_DIR / "settings.json"

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        try:
            return AppSettings.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(settings.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

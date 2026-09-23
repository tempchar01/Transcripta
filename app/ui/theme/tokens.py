"""Central visual tokens for the restrained Transcripta desktop UI."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ThemeMode(StrEnum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


@dataclass(frozen=True, slots=True)
class Palette:
    background: str
    surface: str
    surface_subtle: str
    control: str
    border: str
    control_hover: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent_cyan: str
    accent_blue: str
    accent_violet: str
    success: str
    warning: str
    error: str
    focus: str
    shadow: str


SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 18, "xl": 28, "xxl": 40}
RADIUS = {"control": 7, "surface": 10, "main": 12}
BORDER_WIDTH = {"hairline": 1, "focus": 1}
TYPE = {"brand": 12, "product": 26, "section": 17, "body": 14, "transcript": 15, "caption": 12, "status": 14, "button": 14}
FONT = {"ui": "Segoe UI Variable", "fallback": "Segoe UI"}
FONT_WEIGHT = {"regular": 400, "medium": 500, "semibold": 600}
MOTION_MS = {"hover": 140, "button": 180, "surface": 240}

DARK = Palette(
    background="#1B1E23", surface="#23272E", surface_subtle="#1F2329", control="#2B3038", border="#3C434D",
    control_hover="#343B45", text_primary="#F1F3F5", text_secondary="#BDC4CC", text_muted="#9099A4",
    accent_cyan="#2696B7", accent_blue="#2F87C8", accent_violet="#2F87C8",
    success="#43A784", warning="#C9963E", error="#D66972", focus="#65B8E6", shadow="#00000000",
)
LIGHT = Palette(
    background="#F3F4F6", surface="#FFFFFF", surface_subtle="#F8F9FA", control="#FFFFFF", border="#D6DAE0",
    control_hover="#F5F7F9", text_primary="#20242A", text_secondary="#5C6672", text_muted="#7B858F",
    accent_cyan="#167FA8", accent_blue="#1976B8", accent_violet="#1976B8",
    success="#278260", warning="#9A6A21", error="#B84F59", focus="#167FA8", shadow="#00000000",
)

STATUS_COLORS = {"idle": DARK.accent_blue, "ready": DARK.accent_cyan, "processing": DARK.accent_cyan,
                 "success": DARK.success, "warning": DARK.warning, "error": DARK.error}

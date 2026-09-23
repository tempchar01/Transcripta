"""Locate the one production icon in source and frozen application layouts."""
from __future__ import annotations

import sys
from pathlib import Path


def application_icon_path() -> Path | None:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).parents[2]))
    icon = root / "assets" / "branding" / "generated" / "app_icon.ico"
    return icon if icon.is_file() else None

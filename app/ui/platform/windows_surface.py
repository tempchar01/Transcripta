"""Native-window setup for Transcripta's conventional opaque surface."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


def prepare_opaque_window(window: QWidget) -> None:
    """Use the normal opaque Windows surface; no Acrylic or Mica is requested."""
    window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    window.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
    window.setAutoFillBackground(True)


def ensure_opaque_surface(window: QWidget) -> str:
    prepare_opaque_window(window)
    return "solid-native-surface"

"""Lightweight, custom-painted surfaces for the Transcripta command console."""
from __future__ import annotations

import math
from array import array
from pathlib import Path

from PySide6.QtCore import QObject, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QAbstractButton, QFrame, QWidget

from app.ui.theme.tokens import DARK, LIGHT


def _dark(widget: QWidget) -> bool:
    app = QApplication.instance()
    selected = app.property("transcriptaTheme") if app else None
    return selected == "dark" if selected else widget.palette().windowText().color().lightness() > 128


class CommandSurface(QFrame):
    """Single opaque application surface; drag feedback is supplied by QSS."""
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("commandSurface")


class WaveformIcon(QWidget):
    """Thin neutral waveform mark used only by the empty workspace."""
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(40, 40)

    def paintEvent(self, event) -> None:
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = DARK if _dark(self) else LIGHT
        painter.setPen(QPen(QColor(colors.text_secondary), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        center = self.width() / 2
        baseline = self.height() / 2
        for offset, height in ((-15, 8), (-10, 16), (-5, 25), (0, 13), (5, 31), (10, 18), (15, 9)):
            painter.drawLine(int(center + offset), int(baseline - height / 2), int(center + offset), int(baseline + height / 2))


class ThemeToggleButton(QAbstractButton):
    """A compact vector-only control that shows the theme it will switch to."""
    def __init__(self, current_theme: str, tooltip: str, parent=None) -> None:
        super().__init__(parent)
        self.target_theme = "light"
        self.setCurrentTheme(current_theme)
        self.setToolTip(tooltip); self.setAccessibleName(tooltip)
        self.setFixedSize(38, 38); self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def setCurrentTheme(self, current_theme: str) -> None:
        self.target_theme = "light" if current_theme == "dark" else "dark"
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = DARK if _dark(self) else LIGHT
        rect = QRectF(self.rect()).adjusted(.75, .75, -.75, -.75)
        background = QColor(colors.surface_subtle if self.isDown() else colors.control_hover if self.underMouse() else colors.control)
        border = QColor(colors.focus if self.hasFocus() else colors.accent_blue if self.underMouse() else colors.border)
        painter.setPen(QPen(border, 1)); painter.setBrush(background); painter.drawRoundedRect(rect, 7, 7)
        painter.setPen(QPen(QColor(colors.text_primary), 1.55, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        center = self.rect().center()
        if self.target_theme == "light":
            painter.drawEllipse(center.x() - 4.5, center.y() - 4.5, 9, 9)
            for index in range(8):
                angle = math.tau * index / 8
                inner, outer = 8, 11
                painter.drawLine(int(center.x() + math.cos(angle) * inner), int(center.y() + math.sin(angle) * inner), int(center.x() + math.cos(angle) * outer), int(center.y() + math.sin(angle) * outer))
        else:
            moon = QPainterPath(); moon.moveTo(center.x() + 5, center.y() - 8)
            moon.cubicTo(center.x() - 3, center.y() - 6, center.x() - 6, center.y() + 2, center.x() - 1, center.y() + 7)
            moon.cubicTo(center.x() + 3, center.y() + 11, center.x() + 9, center.y() + 8, center.x() + 10, center.y() + 4)
            moon.cubicTo(center.x() + 4, center.y() + 7, center.x(), center.y(), center.x() + 5, center.y() - 8)
            painter.drawPath(moon)


class HudNavButton(QAbstractButton):
    def __init__(self, text: str, glyph: str, parent=None) -> None:
        super().__init__(parent); self.setText(text); self.glyph = glyph; self.setCheckable(True); self.setMinimumHeight(46); self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event) -> None:
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing); rect = QRectF(self.rect()).adjusted(2, 3, -2, -3)
        active, hover = self.isChecked(), self.underMouse()
        colors = DARK if _dark(self) else LIGHT
        if active or hover or self.hasFocus():
            surface = QColor(colors.accent_blue) if active else QColor(255, 255, 255)
            surface.setAlpha(68 if active else 28)
            painter.setBrush(surface); painter.setPen(QPen(QColor(colors.focus) if self.hasFocus() else QColor(255, 255, 255, 155), 1.2)); painter.drawRoundedRect(rect, 19, 19)
        color = QColor(colors.text_primary if active else colors.text_secondary); painter.setPen(QPen(color, 1.4)); x, y = 18, self.height() / 2
        if self.glyph == "wave":
            for offset, height in ((-7, 5), (-3, 11), (1, 17), (5, 10), (9, 6)):
                painter.drawLine(x + offset, int(y - height / 2), x + offset, int(y + height / 2))
        elif self.glyph == "history":
            painter.drawEllipse(x - 9, int(y - 9), 18, 18); painter.drawLine(x, int(y), x, int(y - 5)); painter.drawLine(x, int(y), x + 4, int(y + 3))
        else:
            # A quiet sliders glyph shares the waveform's line weight and
            # avoids a platform-provided or ornamental settings icon.
            painter.setPen(QPen(color, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for offset, knob in ((-6, 5), (0, -3), (6, 2)):
                line_y = int(y + offset)
                painter.drawLine(x - 9, line_y, x + 9, line_y)
                painter.drawEllipse(x + knob - 2, line_y - 2, 4, 4)
        painter.setPen(QPen(color, 1)); painter.drawText(QRectF(38, 0, self.width() - 42, self.height()), Qt.AlignmentFlag.AlignVCenter, self.text())


class WaveformWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent); self.samples: list[float] = []; self.loading = False; self.setMinimumHeight(125)

    def set_samples(self, samples: list[float]) -> None:
        peak = max(samples, default=0.0)
        # Preserve relative dynamics while making a quiet recording legible at a glance.
        self.samples = [min(1.0, .08 + .92 * value / peak) for value in samples] if peak else []
        self.loading = False; self.update()

    def set_loading(self, loading: bool) -> None:
        self.loading = loading; self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing); rect = QRectF(self.rect()).adjusted(4, 8, -4, -8); mid = rect.center().y()
        grid = QColor("#607DAB" if _dark(self) else "#B8C8DC"); grid.setAlpha(45); painter.setPen(QPen(grid, 1))
        for fraction in (.2, .4, .6, .8): painter.drawLine(int(rect.left() + rect.width() * fraction), int(rect.top()), int(rect.left() + rect.width() * fraction), int(rect.bottom()))
        painter.drawLine(int(rect.left()), int(mid), int(rect.right()), int(mid))
        samples = self.samples or [0.06 + 0.06 * abs(math.sin(index * .71)) for index in range(68)]
        for index, value in enumerate(samples):
            x = rect.left() + (index + .5) * rect.width() / len(samples); height = max(2.5, min(1.0, value) * rect.height() * .78)
            colors = DARK if _dark(self) else LIGHT
            color = QColor(colors.accent_cyan if index / len(samples) < .7 else colors.accent_violet); color.setAlpha(150 if not self.samples else 225)
            painter.setPen(QPen(color, 1.7)); painter.drawLine(int(x), int(mid - height / 2), int(x), int(mid + height / 2))
        if self.loading:
            painter.setPen(QPen(QColor("#B9D8FF"), 1)); painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "…")


class WaveformWorker(QObject):
    ready = Signal(object)
    failed = Signal()
    cancelled = Signal()

    def __init__(self, source: Path, duration: float, bins: int = 88) -> None:
        super().__init__(); self.source, self.duration, self.bins = source, duration, bins; self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            import av
            result: list[float] = []
            with av.open(str(self.source)) as container:
                stream = next(item for item in container.streams if item.type == "audio")
                resampler = av.AudioResampler(format="s16", layout="mono", rate=8_000)
                for position in ((index + .5) * self.duration / self.bins for index in range(self.bins)):
                    if self._cancelled:
                        self.cancelled.emit(); return
                    container.seek(max(0, int(position * av.time_base)), backward=True, any_frame=False)
                    frame = next(container.decode(stream), None)
                    if frame is None:
                        result.append(0.0); continue
                    converted = resampler.resample(frame)
                    converted = converted[0] if converted else None
                    if converted is None:
                        result.append(0.0); continue
                    data = array("h"); data.frombytes(bytes(converted.planes[0]))
                    result.append(min(1.0, sum(abs(item) for item in data) / max(1, len(data)) / 12_000))
            self.ready.emit(result)
        except Exception:
            self.failed.emit()


class ProcessIndicator(QWidget):
    def __init__(self, translate, parent=None) -> None:
        super().__init__(parent); self.translate, self.stage = translate, 0; self.setMinimumHeight(48)

    def set_stage(self, stage: int) -> None:
        self.stage = max(0, min(2, stage)); self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing); labels = (self.translate("stage_load"), self.translate("stage_processing"), self.translate("stage_ready")); width = self.width() / 3
        for index, label in enumerate(labels):
            x, active = width * (index + .5), index <= self.stage
            colors = DARK if _dark(self) else LIGHT
            color = QColor(colors.accent_blue if active else colors.text_muted); color.setAlpha(255 if index == self.stage else 190)
            painter.setBrush(color if index == self.stage else Qt.BrushStyle.NoBrush); painter.setPen(QPen(color, 1)); painter.drawEllipse(int(x - 13), 4, 26, 26)
            painter.setPen(QPen(QColor("#FFFFFF") if index == self.stage else color, 1)); painter.drawText(QRectF(x - 13, 4, 26, 26), Qt.AlignmentFlag.AlignCenter, str(index + 1))
            painter.setPen(QPen(color, 1)); painter.drawText(QRectF(x - width / 2 + 30, 34, width - 60, 14), Qt.AlignmentFlag.AlignCenter, label.upper())
            if index < 2:
                line_color = QColor("#6D91BF"); line_color.setAlpha(120 if index < self.stage else 45); painter.setPen(QPen(line_color, 1)); painter.drawLine(int(x + 22), 17, int(x + width - 22), 17)

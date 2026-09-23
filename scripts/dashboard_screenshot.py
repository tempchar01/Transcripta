"""Render a repeatable offscreen dashboard screenshot for visual review."""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from app.config.settings import SettingsStore
from app.ui.main_window import MainWindow
from app.ui.theme.manager import ThemeManager


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--language", choices=("ru", "en"), default="ru")
    parser.add_argument("--theme", choices=("dark", "light"), default="dark")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--state", choices=("empty", "loaded", "processing", "ready"), default="empty")
    args = parser.parse_args()
    app = QApplication.instance() or QApplication([])
    # Qt's Windows offscreen plugin has no system font database; load the same UI
    # family explicitly so review captures contain the actual Cyrillic labels.
    QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\segoeui.ttf")
    store = SettingsStore(Path("work") / "dashboard-screenshot-settings.json")
    settings = store.load(); settings.general.theme = args.theme; settings.general.language = args.language; store.save(settings)
    ThemeManager.apply(app, args.theme)
    window = MainWindow(store); window.resize(args.width, args.height); window.show()
    if args.source:
        window.set_source(args.source)
    if args.state == "processing":
        window._set_running(True)
        window.progress.setValue(63); window.progress_percent.setText("63%")
        window.progress_details.setText(window.t("progress_details", processed="06:14", duration="14:51", eta="1 мин"))
        window.status.setText("")
    elif args.state == "ready":
        exported = {"docx": Path("output") / "meeting.docx"}
        window.last_result = SimpleNamespace(exported=exported)
        window._show_ready_result(exported)
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        app.processEvents(); time.sleep(.02)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    window.grab().save(str(args.output))
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

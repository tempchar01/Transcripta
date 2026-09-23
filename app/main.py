from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.branding import PRODUCT_NAME, application_icon
from app.config.settings import APP_DATA_DIR, SettingsStore
from app.ui.main_window import MainWindow
from app.utils.logging import configure_logging


def main() -> int:
    logger = configure_logging(APP_DATA_DIR / "logs")
    app = QApplication(sys.argv)
    app.setApplicationName(PRODUCT_NAME)
    app.setWindowIcon(application_icon(logger))
    window = MainWindow(SettingsStore())
    window.setWindowIcon(app.windowIcon())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

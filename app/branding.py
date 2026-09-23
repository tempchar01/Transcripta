from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtGui import QIcon
from app.ui.assets import application_icon_path


APP_NAME = "TRANSCRIPTA"
MODULE_NAME = "Transcripta"
PRODUCT_NAME = MODULE_NAME
INSTALLER_PRODUCT_NAME = MODULE_NAME
CREATOR_NAME = "Maksim Pershikov"
CONTACT_EMAIL = "tempchar1@outlook.com"
SUPPORT_URL = "https://app.lava.top/tempchar"
TELEGRAM_HANDLE = "@tempchar1"
TELEGRAM_URL = "https://t.me/tempchar1"
INSTAGRAM_HANDLE = "@tempchar_"
INSTAGRAM_URL = "https://www.instagram.com/tempchar_/"
BRANDING_DIR = Path(__file__).parent.parent / "assets" / "branding"
APP_ICON_PATH = application_icon_path()


def application_icon(logger: logging.Logger | None = None) -> QIcon:
    """Return the replaceable branded icon without making a missing asset fatal."""
    asset = application_icon_path()
    if asset and asset.is_file():
        return QIcon(str(asset))
    (logger or logging.getLogger("transcripta")).warning("Application icon is missing: %s", APP_ICON_PATH)
    return QIcon()

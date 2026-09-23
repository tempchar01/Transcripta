from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from app.config.settings import AppSettings, SettingsStore
from app.ui.i18n import Translator
from app.ui.theme.manager import ThemeManager
from app.ui.theme.tokens import DARK, ThemeMode


def test_translator_switches_without_strings_in_widgets():
    assert Translator("ru")("choose_file") == "Выбрать файл"
    assert Translator("en")("choose_file") == "Choose file"


def test_theme_manager_applies_explicit_dark_palette():
    application = QApplication.instance() or QApplication([])
    assert ThemeManager.apply(application, "dark") is ThemeMode.DARK
    assert DARK.text_primary in application.styleSheet()


@pytest.mark.parametrize("mode,is_dark", [("light", False), ("dark", True)])
def test_selected_neutral_palette_does_not_override_the_resolved_theme(mode, is_dark):
    from PySide6.QtWidgets import QWidget
    from app.ui.dashboard import _dark
    application = QApplication.instance() or QApplication([])
    ThemeManager.apply(application, mode)
    widget = QWidget()
    try:
        assert widget.palette().window().color().alpha() == 255
        assert _dark(widget) is is_dark
    finally:
        widget.close()


def test_general_preferences_are_persisted(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    settings = AppSettings(); settings.general.language = "en"; settings.general.theme = "dark"
    store.save(settings)
    restored = store.load()
    assert restored.general.language == "en"
    assert restored.general.theme == "dark"

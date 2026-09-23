from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from app.ui.theme.tokens import DARK, FONT, LIGHT, Palette, ThemeMode, TYPE, RADIUS


class ThemeManager:
    @staticmethod
    def resolved(mode: str | ThemeMode, app: QApplication) -> ThemeMode:
        selected = ThemeMode(mode)
        if selected is not ThemeMode.SYSTEM:
            return selected
        return ThemeMode.DARK if app.styleHints().colorScheme() == Qt.ColorScheme.Dark else ThemeMode.LIGHT

    @classmethod
    def apply(cls, app: QApplication, mode: str | ThemeMode) -> ThemeMode:
        resolved = cls.resolved(mode, app)
        colors = DARK if resolved is ThemeMode.DARK else LIGHT
        app.setProperty("transcriptaTheme", resolved.value)
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(colors.background))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(colors.text_primary))
        palette.setColor(QPalette.ColorRole.Base, QColor(colors.surface))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors.surface_subtle))
        palette.setColor(QPalette.ColorRole.Text, QColor(colors.text_primary))
        palette.setColor(QPalette.ColorRole.Button, QColor(colors.control))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors.text_primary))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors.accent_blue))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        app.setPalette(palette)
        app.setStyleSheet(cls.stylesheet(colors))
        from app.ui.platform.windows_surface import ensure_opaque_surface
        for window in app.topLevelWidgets():
            if getattr(window, "_surface_applied", False):
                window._surface_backend = ensure_opaque_surface(window)
            window.update()
        return resolved

    @staticmethod
    def stylesheet(colors: Palette) -> str:
        dialog = colors.surface
        return f"""
        * {{ font-family: '{FONT['ui']}', '{FONT['fallback']}', sans-serif; font-size: {TYPE['body']}px; color: {colors.text_primary}; }}
        QMainWindow, QWidget#dashboardRoot {{ background: {colors.background}; }}
        QWidget#contentColumn, QWidget#workspacePanel, QWidget#sourcePage, QWidget#emptyPage, QWidget#readyPage, QWidget#processingPage, QWidget#processingContent, QStackedWidget#workspaceStack {{ background: transparent; border: 0; }}
        QFrame#commandSurface {{ background: {colors.surface}; border: 1px solid {colors.border}; border-radius: {RADIUS['main']}px; }}
        QFrame#commandSurface[dragActive="true"] {{ border-color: {colors.accent_blue}; }}
        QDialog {{ background: {dialog}; }}
        QLabel {{ background: transparent; }}
        QLabel#wordmark {{ font-size: {TYPE['product']}px; font-weight: 600; color: {colors.text_primary}; }}
        QLabel#subtitle {{ color: {colors.text_secondary}; font-size: 13px; }}
        QLabel#muted, QLabel#metadata, QLabel#workspaceStatus {{ color: {colors.text_secondary}; font-size: {TYPE['caption']}px; }}
        QLabel#workspaceStatus {{ font-size: {TYPE['status']}px; }}
        QLabel#fileName {{ font-size: {TYPE['body']}px; font-weight: 600; }}
        QLabel#fileMeta {{ color: {colors.text_secondary}; font-size: {TYPE['caption']}px; }}
        QLabel#emptyHint {{ color: {colors.text_primary}; font-size: 16px; font-weight: 500; }}
        QLabel#emptySubhint {{ color: {colors.text_secondary}; font-size: 13px; }}
        QLabel#progressPercent {{ font-size: 32px; font-weight: 600; color: {colors.text_primary}; }}
        QLabel#progressDetails {{ color: {colors.text_secondary}; font-size: 13px; line-height: 1.35; }}
        QLabel#processingTitle {{ font-size: {TYPE['section']}px; font-weight: 600; color: {colors.text_primary}; }}
        QLabel#readyTitle {{ font-size: {TYPE['product']}px; font-weight: 600; color: {colors.text_primary}; }}
        QLabel#readyOutput {{ color: {colors.text_secondary}; font-size: 14px; }}
        QLabel#controlLabel {{ color: {colors.text_secondary}; font-size: {TYPE['caption']}px; font-weight: 500; }}
        QPushButton {{ background: {colors.control}; border: 1px solid {colors.border}; border-radius: {RADIUS['control']}px; padding: 8px 15px; min-height: 22px; font-size: {TYPE['button']}px; font-weight: 500; }}
        QPushButton:hover {{ background: {colors.control_hover}; border-color: {colors.accent_blue}; }}
        QPushButton:pressed {{ background: {colors.surface_subtle}; border-color: {colors.accent_blue}; }}
        QPushButton:focus, QComboBox:focus {{ border: 1px solid {colors.focus}; }}
        QPushButton#chooseSource {{ padding: 10px 22px; font-weight: 600; }}
        QPushButton#clearSource {{ padding: 0; border-radius: 7px; min-height: 28px; }}
        QPushButton#primary {{ background: {colors.accent_blue}; color: #FFFFFF; border: 1px solid {colors.accent_blue}; border-radius: {RADIUS['control']}px; padding: 10px 24px; min-height: 26px; font-size: {TYPE['button']}px; font-weight: 600; }}
        QPushButton#primary:hover {{ background: {colors.accent_cyan}; border-color: {colors.accent_cyan}; }}
        QPushButton#primary:pressed {{ background: {colors.focus}; border-color: {colors.focus}; }}
        QPushButton#danger {{ color: {colors.error}; }}
        QPushButton:disabled, QPushButton#primary:disabled {{ background: {colors.surface_subtle}; color: {colors.text_muted}; border-color: {colors.border}; }}
        QComboBox, QLineEdit, QSpinBox {{ background: {colors.control}; border: 1px solid {colors.border}; border-radius: {RADIUS['control']}px; padding: 7px 10px; min-height: 22px; font-size: {TYPE['body']}px; }}
        QComboBox:hover, QLineEdit:hover, QSpinBox:hover {{ border-color: {colors.accent_blue}; }}
        QComboBox::drop-down {{ border: 0; width: 24px; }}
        QComboBox QAbstractItemView {{ background: {dialog}; color: {colors.text_primary}; selection-background-color: {colors.accent_blue}; selection-color: #FFFFFF; border: 1px solid {colors.border}; outline: 0; padding: 4px; }}
        QProgressBar {{ background: {colors.surface_subtle}; border: 1px solid {colors.border}; min-height: 12px; max-height: 12px; border-radius: 6px; text-align: center; }}
        QProgressBar::chunk {{ background: {colors.accent_blue}; border-radius: 5px; }}
        QScrollBar:vertical {{ background: {colors.surface_subtle}; width: 10px; margin: 0; border-radius: 5px; }}
        QScrollBar::handle:vertical {{ background: {colors.text_muted}; border-radius: 5px; min-height: 32px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """

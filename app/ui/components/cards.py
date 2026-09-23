from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QComboBox, QDialog, QFrame, QPushButton, QProgressBar, QToolTip


class CardFrame(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")


class DropCard(CardFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("dropCard")


class GlassPanel(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("glassPanel")


class GlassCard(GlassPanel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("glassCard")


class GlassButton(QPushButton):
    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("glassButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class GlassDropdown(QComboBox):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("glassDropdown")


class GlassProgress(QProgressBar):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("glassProgress")


class GlassDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("glassDialog")


class GlassSidebarItem(GlassButton):
    def __init__(self, text: str = "", icon: QIcon | None = None, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("glassSidebarItem")
        if icon is not None:
            self.setIcon(icon); self.setIconSize(QSize(16, 16))


class GlassSegmentedControl(GlassPanel):
    """Container contract for future compact mode selectors; intentionally behavior-neutral."""
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("glassSegmentedControl")


GlassTooltip = QToolTip

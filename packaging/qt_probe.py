"""Temporary release-build diagnostic for PySide6 DLL loading."""
from PySide6 import QtCore
print("QtCore", QtCore.qVersion())
from PySide6 import QtGui
print("QtGui")
from PySide6 import QtWidgets
print("QtWidgets")

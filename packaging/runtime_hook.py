"""Keep frozen runtime streams independent of developer console handles."""
import os
import sys

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
    # Qt DLLs live next to its extension modules in PyInstaller's `_internal`
    # layout. Keep this handle alive before the first QtWidgets import.
    _PYSIDE_DLL_DIRECTORY = os.add_dll_directory(os.path.join(sys._MEIPASS, "PySide6"))
# Do not import application modules here. The unchanged GPU probe activates
# package-local CUDA paths immediately before CTranslate2 loads.

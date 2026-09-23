# Central Windows x64 one-folder release specification.
from pathlib import Path
import runpy

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct

ROOT = Path(SPECPATH).parent
APP = ROOT / "app"
release = runpy.run_path(str(APP / "release.py"))
PRODUCTION_ICON = ROOT / "assets" / "branding" / "generated" / "app_icon.ico"
ICON = PRODUCTION_ICON if PRODUCTION_ICON.is_file() else APP / "ui" / "assets" / "branding" / "app_icon.ico"

assert ICON.is_file(), "Production icon missing"
datas = [(str(ICON), "assets/branding/generated")]
if (ROOT / "build" / "release-licenses").is_dir():
    datas += [(str(ROOT / "build" / "release-licenses"), "licenses")]
binaries = []
for package in ("ctranslate2", "av", "nvidia.cublas", "faster_whisper", "docx"):
    datas += collect_data_files(package)
    binaries += collect_dynamic_libs(package)
for package in ("faster-whisper", "PySide6", "python-docx", "nvidia-cublas-cu12"):
    datas += copy_metadata(package, recursive=True)

version = VSVersionInfo(ffi=FixedFileInfo(filevers=release["WINDOWS_VERSION"], prodvers=release["WINDOWS_VERSION"], mask=0x3f, flags=2, OS=0x40004, fileType=1, subtype=0, date=(0, 0)), kids=[
    StringFileInfo([StringTable("040904B0", [StringStruct(key, value) for key, value in {
        "CompanyName": release["PUBLISHER"], "FileDescription": release["DESCRIPTION"],
        "FileVersion": release["VERSION"], "ProductVersion": release["VERSION"],
        "ProductName": release["PRODUCT"], "OriginalFilename": "Transcripta.exe",
        "LegalCopyright": "Copyright Maksim Pershikov"}.items()])]),
    VarFileInfo([VarStruct("Translation", [1033, 1200])])])
a = Analysis([str(ROOT / "packaging" / "launcher.py")], pathex=[str(ROOT)], binaries=binaries, datas=datas,
             hiddenimports=["app.hardware.nvidia_runtime", "av", "onnxruntime"],
             runtime_hooks=[str(ROOT / "packaging" / "runtime_hook.py")],
             excludes=["torch", "tensorflow", "transformers", "matplotlib", "pandas", "scipy", "sympy",
                       "pytest", "IPython", "notebook", "tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets"], noarchive=False)
# A dependency wheel can carry bytecode caches next to license material. They
# are neither imports nor license text and must not enter a production bundle.
a.datas = [entry for entry in a.datas if "__pycache__" not in Path(entry[0]).parts]
# PySide6 uses the Windows system ICU. Developer tools can put an unrelated
# unversioned Poppler ICU on PATH; PyInstaller must never copy that DLL into
# the application where it would shadow the compatible Windows runtime.
external_icu = {"icudt.dll", "icudt78.dll", "icuin.dll", "icuuc.dll"}
a.binaries = [entry for entry in a.binaries if Path(entry[0]).name.lower() not in external_icu]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Transcripta", icon=str(ICON), version=version, console=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="Transcripta", upx=False)

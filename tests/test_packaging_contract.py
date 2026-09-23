from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_packaging_and_installer_share_the_controlled_icon_contract():
    spec = (ROOT / "packaging" / "transcripta.spec").read_text(encoding="utf-8")
    installer = (ROOT / "installer" / "Transcripta.iss").read_text(encoding="utf-8")
    assert "app_icon.ico" in spec
    assert '"generated" / "app_icon.ico"' in spec
    assert 'name="Transcripta"' in spec
    assert 'ProductName "Transcripta"' in installer
    assert "SetupIconFile={#BrandIcon}" in installer
    assert "UninstallDisplayIcon={app}\\{#ProductExe}" in installer
    assert '#define InstalledIcon "{app}\\_internal\\assets\\branding\\generated\\app_icon.ico"' in installer
    assert 'IconFilename: "{#InstalledIcon}"' in installer
    assert "Languages\\Russian.isl" in installer
    assert "%LOCALAPPDATA%\\Transcripta is intentionally never deleted" in installer


def test_generated_icon_is_a_multi_size_windows_ico():
    from PIL import Image

    icon = ROOT / "assets" / "branding" / "generated" / "app_icon.ico"
    assert icon.is_file()
    with Image.open(icon) as image:
        assert {(16, 16), (20, 20), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)}.issubset(image.ico.sizes())


def test_build_excludes_developer_path_icu_from_the_standalone_runtime():
    spec = (ROOT / "packaging" / "transcripta.spec").read_text(encoding="utf-8")
    script = (ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")
    assert '"icuuc.dll"' in spec
    assert "a.binaries = [entry for entry in a.binaries" in spec
    assert '$env:PATH = "$env:SystemRoot\\System32;$env:SystemRoot"' in script
    assert script.index('$env:PATH = "$env:SystemRoot\\System32;$env:SystemRoot"') < script.index("-m PyInstaller")

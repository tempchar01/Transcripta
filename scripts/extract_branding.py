"""Create controlled icon derivatives from the user-supplied branding board.

The source image is never modified. Change --crop only after visual approval of the
selected rectangle; this script exists to make the one-time extraction reproducible.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "assets" / "branding" / "ChatGPT Image 6 сент. 2026 г., 21_55_31.png"
OUTPUT = ROOT / "assets" / "branding" / "generated"
SIZES = (16, 24, 32, 48, 64, 128, 256)
# App-icon master panel in the supplied 1254×1254 branding board.
DEFAULT_CROP = (716, 78, 944, 306)


def extract(source: Path = SOURCE, output: Path = OUTPUT, crop: tuple[int, int, int, int] = DEFAULT_CROP) -> tuple[Path, Path, Path]:
    if not source.is_file():
        raise FileNotFoundError(source)
    output.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as board:
        master = board.convert("RGBA").crop(crop).resize((1024, 1024), Image.Resampling.LANCZOS)
    master_path, icon_256, ico = output / "app_icon_master.png", output / "app_icon_256.png", output / "app_icon.ico"
    master.save(master_path); master.resize((256, 256), Image.Resampling.LANCZOS).save(icon_256)
    master.save(ico, format="ICO", sizes=[(size, size) for size in SIZES])
    return master_path, icon_256, ico


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--crop", type=int, nargs=4, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"), default=DEFAULT_CROP)
    args = parser.parse_args()
    paths = extract(args.source, args.output, tuple(args.crop))
    print("\n".join(str(path) for path in paths)); return 0


if __name__ == "__main__":
    raise SystemExit(main())

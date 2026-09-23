"""Build Transcripta's canonical multi-resolution Windows icon from its PNG source."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


SIZES = (256, 128, 64, 48, 32, 24, 20, 16)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--proof", type=Path)
    args = parser.parse_args()

    with Image.open(args.source) as original:
        image = original.convert("RGBA")
    if image.width != image.height:
        raise ValueError(f"Canonical icon must be square, got {image.size}")
    if image.width < max(SIZES):
        raise ValueError(f"Canonical icon must be at least {max(SIZES)}px, got {image.size}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="ICO", sizes=[(size, size) for size in SIZES])

    if args.proof:
        cells = [image.resize((size, size), Image.Resampling.LANCZOS) for size in SIZES]
        cell_width, cell_height = 256, 288
        sheet = Image.new("RGBA", (cell_width * 4, cell_height * 2), (20, 25, 39, 255))
        for index, (size, cell) in enumerate(zip(SIZES, cells)):
            x, y = (index % 4) * cell_width, (index // 4) * cell_height
            sheet.alpha_composite(cell, (x + (cell_width - size) // 2, y + 16))
            # Use a fixed visible caption without introducing another font asset.
            from PIL import ImageDraw
            ImageDraw.Draw(sheet).text((x + 12, y + 264), f"{size} × {size}", fill=(230, 238, 255, 255))
        args.proof.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(args.proof)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

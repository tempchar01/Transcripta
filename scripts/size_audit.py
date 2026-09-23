"""Report the size and duplicate files in a candidate packaged distribution.

No packager is required: run this against a PyInstaller/Nuitka output directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _group(relative: Path) -> str:
    """Classify a release tree without assuming one packager's layout."""
    parts = {part.lower() for part in relative.parts}
    name = relative.name.lower()
    if any("pyside6" in part for part in parts): return "PySide6"
    if any(part.startswith("qt") for part in parts): return "Qt plugins/locales"
    if "ctranslate2" in "\\".join(parts): return "CTranslate2"
    if "nvidia" in "\\".join(parts) or "cublas" in name or "cudnn" in name: return "CUDA-cuBLAS-cuDNN"
    if name.startswith(("av", "libav")) or any(part == "av" for part in parts): return "PyAV"
    if name.startswith(("ffmpeg", "ffprobe")) or "ffmpeg" in parts: return "FFmpeg"
    if name.endswith((".pdb", ".map")): return "debug files"
    if name.endswith(".pyc") or "__pycache__" in parts: return "bytecode"
    if any(part in {"tests", "docs", "examples", ".cache"} for part in parts): return "non-runtime candidates"
    if len(relative.parts) == 1 and name.endswith(".exe"): return "application/runtime"
    return "application and other"


def audit(root: Path) -> dict[str, object]:
    root = root.resolve()
    groups: dict[str, int] = defaultdict(int)
    hashes: dict[str, list[str]] = defaultdict(list)
    total = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        size = path.stat().st_size; total += size
        relative = path.relative_to(root)
        group = _group(relative)
        groups[group] += size
        hashes[_hash(path)].append(relative.as_posix())
    duplicates = [sorted(files) for files in hashes.values() if len(files) > 1]
    return {"root": str(root), "total_bytes": total, "groups_bytes": dict(sorted(groups.items())), "duplicate_sets": duplicates}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")
    args = parser.parse_args(); report = audit(args.root)
    if args.json: print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Distribution: {report['root']}\nTotal: {report['total_bytes'] / 1024 / 1024:.1f} MiB")
        for group, size in report["groups_bytes"].items(): print(f"  {group}: {size / 1024 / 1024:.1f} MiB")
        print(f"Duplicate content sets: {len(report['duplicate_sets'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

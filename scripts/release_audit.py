"""Read-only source inventory plus generated dependency/license release evidence."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
import shutil
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("PySide6", "faster-whisper", "ctranslate2", "huggingface-hub", "tqdm", "av", "python-docx", "nvidia-cublas-cu12")


def ui_hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / "app" / "ui").rglob("*") if p.is_file() and "__pycache__" not in p.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--licenses", type=Path)
    args = parser.parse_args()
    inventory, errors = {}, []
    for folder, dirs, files in os.walk(ROOT, onerror=lambda e: errors.append(str(e))):
        for name in files:
            path = Path(folder) / name
            relative = path.relative_to(ROOT)
            group = relative.parts[0]
            try:
                inventory[group] = inventory.get(group, 0) + path.stat().st_size
            except OSError as error:
                errors.append(str(error))
    pending, seen, packages = list(RUNTIME), set(), []
    while pending:
        name = pending.pop()
        dist = metadata.distribution(name)
        key = dist.metadata['Name'].lower().replace('_', '-')
        if key in seen:
            continue
        seen.add(key)
        size = 0
        for file in dist.files or []:
            path = Path(dist.locate_file(file))
            if not path.is_file():
                continue
            size += path.stat().st_size
            if args.licenses and any(word in path.name.lower() for word in ("license", "copying", "notice")):
                if path.suffix.lower() not in {".py", ".pyc", ".pyd", ".dll"}:
                    target = args.licenses / key / path.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
        packages.append({"package": dist.metadata['Name'], "version": dist.version, "installed_bytes": size,
                         "license": dist.metadata.get('License-Expression') or dist.metadata.get('License') or
                         '; '.join(v for v in dist.metadata.get_all('Classifier', []) if v.startswith('License')),
                         "runtime": True, "decision": "keep"})
        for dependency in dist.requires or []:
            requirement = Requirement(dependency)
            if not requirement.marker or requirement.marker.evaluate({"extra": ""}):
                pending.append(requirement.name)
    report = {"inventory_bytes": inventory, "inventory_errors": errors,
              "packages": sorted(packages, key=lambda x: x['package'].lower()), "ui_sha256": ui_hashes(),
              "free_bytes": shutil.disk_usage(ROOT).free,
              "excluded_from_distribution": ["avatar assets", "source artwork", "Remotion", "Node", "tests", "docs", "work", "models", "logs", "dev caches"],
              "deleted_source_files": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Audited {len(packages)} runtime distributions; {len(errors)} inaccessible inventory entries")


if __name__ == '__main__':
    main()

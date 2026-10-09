"""Collect installed runtime license texts and exact versions for redistribution."""
from __future__ import annotations

import importlib.metadata as metadata
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
DIRECT = ("aiohttp", "mss", "Pillow")


def collect() -> None:
    queue = list(DIRECT)
    seen: set[str] = set()
    components = []
    destination = ROOT / "licenses" / "python"
    destination.mkdir(parents=True, exist_ok=True)
    while queue:
        name = queue.pop(0)
        key = name.lower().replace("_", "-")
        if key in seen:
            continue
        seen.add(key)
        dist = metadata.distribution(name)
        out = destination / f"{dist.metadata['Name']}-{dist.version}"
        out.mkdir(exist_ok=True)
        copied = []
        copied_sboms = []
        for entry in dist.files or ():
            # Distribution metadata includes full upstream notices, including Pillow's
            # bundled image-library notices. Preserve their original filenames.
            if ".dist-info/" in str(entry).replace("\\", "/") and any(
                term in entry.name.lower() for term in ("license", "copying", "notice")
            ):
                target = out / entry.name
                shutil.copyfile(dist.locate_file(entry), target)
                copied.append(str(target.relative_to(ROOT)).replace("\\", "/"))
            if ".dist-info/sboms/" in str(entry).replace("\\", "/"):
                # Preserve publisher SBOMs verbatim. These may describe optional
                # capabilities too, so runtime feature auditing is separate.
                relative = str(entry).replace("\\", "/").split(".dist-info/", 1)[1]
                target = out / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(dist.locate_file(entry), target)
                copied_sboms.append(str(target.relative_to(ROOT)).replace("\\", "/"))
        if not copied:
            raise RuntimeError(f"No installed license found for {name}")
        components.append({"name": dist.metadata["Name"], "version": dist.version,
                           "license": dist.metadata.get("License-Expression") or dist.metadata.get("License"),
                           "project_urls": dist.metadata.get_all("Project-URL") or [],
                           "license_files": copied, "sbom_files": copied_sboms})
        for requirement in dist.requires or ():
            from packaging.requirements import Requirement
            req = Requirement(requirement)
            if req.marker is None or req.marker.evaluate({"extra": ""}):
                queue.append(req.name)
    python_root = Path(sys.base_prefix)
    shutil.copyfile(python_root / "LICENSE.txt", destination / "CPython-LICENSE.txt")
    for source in (python_root / "tcl").rglob("license*"):
        if source.is_file():
            relative = source.relative_to(python_root / "tcl")
            target = destination / "tcl-tk" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    components.sort(key=lambda x: x["name"].lower())
    (ROOT / "licenses" / "python-components.json").write_text(
        json.dumps(components, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / "desktop" / "requirements-lock.txt").write_text(
        "# Runtime dependency lock generated from the verified Windows build.\n" +
        "\n".join(f"{c['name']}=={c['version']}" for c in components) + "\n", encoding="utf-8")
    print(f"Collected full license texts for {len(components)} Python runtime dependencies.")


if __name__ == "__main__":
    collect()

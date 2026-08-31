#!/usr/bin/env python3
"""Apply the staged Project Radar v2 source bundle on its feature branch."""

from __future__ import annotations

import base64
import hashlib
import io
import tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PART_DIR = ROOT / ".github" / "bootstrap" / "project-radar-v2"
EXPECTED_PARTS = [f"part-{index:02d}" for index in range(9)]
EXPECTED_SHA256 = "be0a46d08820b8032c108f2089255960ebffd977e01e8a72130926a30b074863"
EXPECTED_FILES = 30
WORKFLOW_PREFIX = ".github/workflows/"


def main() -> int:
    parts = sorted(PART_DIR.glob("part-*"))
    actual_names = [path.name for path in parts]
    if actual_names != EXPECTED_PARTS:
        raise RuntimeError(f"staged part set is incomplete: {actual_names!r}")

    encoded = "".join(path.read_text(encoding="ascii").strip() for path in parts)
    raw = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError(f"archive digest mismatch: {digest}")

    root = ROOT.resolve()
    extracted = 0
    skipped_workflows = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:xz") as archive:
        members = archive.getmembers()
        if len(members) != EXPECTED_FILES:
            raise RuntimeError(f"expected {EXPECTED_FILES} files, found {len(members)}")
        for member in members:
            if not member.isfile():
                raise RuntimeError(f"archive contains a non-file member: {member.name}")
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError(f"unsafe archive path: {member.name}")
            if member.name.startswith(WORKFLOW_PREFIX):
                skipped_workflows += 1
                continue
            target = (ROOT / relative).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"unsafe resolved path: {member.name}")
            source = archive.extractfile(member)
            if source is None:
                raise RuntimeError(f"unable to read archive member: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read())
            extracted += 1

    print(
        f"Applied {extracted} Project Radar v2 files; "
        f"deferred {skipped_workflows} workflow files to the reviewed cleanup commit."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Inventory two PSP ISO9660 images and extract only differing files.

This script never opens either source image for writing.  Its JSON/CSV reports
record the path, extent, size, sector allocation, and SHA-256 of every file so
later conclusions can be tied back to exact artifacts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from hanpatch.platforms.psp import iso9660


CHUNK = 8 * 1024 * 1024


def sha256_extent(blob, start: int, size: int) -> str:
    digest = hashlib.sha256()
    end = start + size
    at = start
    while at < end:
        nxt = min(at + CHUNK, end)
        digest.update(blob[at:nxt])
        at = nxt
    return digest.hexdigest()


def inventory(path: Path) -> dict:
    rows = []
    with iso9660.Iso.from_path(path) as iso:
        for entry in sorted(iso.walk(), key=lambda item: item.path):
            if entry.is_dir:
                continue
            rows.append(
                {
                    "path": entry.path,
                    "size": entry.size,
                    "lba": entry.lba,
                    "offset": entry.offset,
                    "sectors": iso9660.sectors_for(entry.size),
                    "record_offset": entry.record_offset,
                    "sha256": sha256_extent(iso.blob, entry.offset, entry.size),
                }
            )
        return {
            "image": str(path.resolve()),
            "image_size": path.stat().st_size,
            "image_sha256": file_sha256(path),
            "volume_id": iso.volume_id,
            "volume_space": iso.volume_space,
            "block_size": iso.block_size,
            "files": rows,
        }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def write_inventory(out_dir: Path, label: str, data: dict) -> None:
    (out_dir / f"iso_inventory_{label}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (out_dir / f"iso_inventory_{label}.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data["files"][0]))
        writer.writeheader()
        writer.writerows(data["files"])


def compare(left: dict, right: dict) -> list[dict]:
    a = {row["path"].upper(): row for row in left["files"]}
    b = {row["path"].upper(): row for row in right["files"]}
    rows = []
    for key in sorted(set(a) | set(b)):
        old = a.get(key)
        new = b.get(key)
        if old is None:
            status = "patched_only"
        elif new is None:
            status = "original_only"
        elif old["sha256"] == new["sha256"]:
            status = "same"
        else:
            status = "changed"
        rows.append(
            {
                "path": (old or new)["path"],
                "status": status,
                "original_size": None if old is None else old["size"],
                "patched_size": None if new is None else new["size"],
                "size_delta": None
                if old is None or new is None
                else new["size"] - old["size"],
                "original_lba": None if old is None else old["lba"],
                "patched_lba": None if new is None else new["lba"],
                "original_sha256": None if old is None else old["sha256"],
                "patched_sha256": None if new is None else new["sha256"],
            }
        )
    return rows


def extract_selected(image: Path, out_dir: Path, selected: set[str]) -> None:
    with iso9660.Iso.from_path(image) as iso:
        for entry in iso.walk():
            if entry.is_dir or entry.path.upper() not in selected:
                continue
            target = out_dir / entry.path.lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                start = entry.offset
                end = start + entry.size
                at = start
                while at < end:
                    nxt = min(at + CHUNK, end)
                    handle.write(iso.blob[at:nxt])
                    at = nxt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("patched", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    original = inventory(args.original)
    patched = inventory(args.patched)
    write_inventory(args.out, "original", original)
    write_inventory(args.out, "patched", patched)

    diff = compare(original, patched)
    (args.out / "iso_diff.json").write_text(
        json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (args.out / "iso_diff.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(diff[0]))
        writer.writeheader()
        writer.writerows(diff)

    selected = {
        row["path"].upper()
        for row in diff
        if row["status"] in {"changed", "original_only", "patched_only"}
    }
    extract_selected(args.original, args.out / "changed" / "original", selected)
    extract_selected(args.patched, args.out / "changed" / "patched", selected)

    summary = {
        "original_file_count": len(original["files"]),
        "patched_file_count": len(patched["files"]),
        "same": sum(row["status"] == "same" for row in diff),
        "changed": sum(row["status"] == "changed" for row in diff),
        "original_only": sum(row["status"] == "original_only" for row in diff),
        "patched_only": sum(row["status"] == "patched_only" for row in diff),
    }
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

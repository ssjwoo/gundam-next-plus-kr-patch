#!/usr/bin/env python3
"""Inventory and optionally extract Sega AFS archives used by the PSP title."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mmap
import os
import struct
from collections import Counter
from pathlib import Path


CHUNK = 8 * 1024 * 1024
ENTRY = 8
DIR_ENTRY = 48


def decode_name(raw: bytes) -> str:
    raw = raw.split(b"\0", 1)[0]
    for codec in ("cp932", "ascii", "latin-1"):
        try:
            return raw.decode(codec)
        except UnicodeDecodeError:
            pass
    return raw.hex()


def magic_label(head: bytes) -> str:
    signatures = (
        (b"AFS\0", "AFS"),
        (b"TIM2", "TIM2"),
        (b"MIG.00.1PSP", "GIM"),
        (b"RIFF", "RIFF"),
        (b"OggS", "OGG"),
        (b"PSMF", "PMF"),
        (b"\x7fELF", "ELF"),
        (b"~PSP", "PSP_ENCRYPTED"),
        (b"~SCE", "SCE_ENCRYPTED"),
        (b"\x89PNG\r\n\x1a\n", "PNG"),
        (b"BM", "BMP"),
    )
    for signature, label in signatures:
        if head.startswith(signature):
            return label
    if not head or all(byte == 0 for byte in head):
        return "ZERO"
    if head[:4] == b"VAGp":
        return "VAG"
    return head[:4].hex().upper()


def classify(name: str, magic: str) -> str:
    ext = Path(name).suffix.lower()
    if magic in {"TIM2", "GIM", "PNG", "BMP"} or ext in {
        ".tm2", ".tim", ".tim2", ".gim", ".png", ".bmp", ".tga", ".dds"
    }:
        return "image"
    if magic in {"RIFF", "OGG", "VAG"} or ext in {
        ".at3", ".wav", ".adx", ".vag", ".mp3", ".ogg"
    }:
        return "audio"
    if magic == "PMF" or ext in {".pmf", ".mpg", ".mpeg"}:
        return "video"
    if ext in {".txt", ".csv", ".tsv", ".msg", ".mes", ".tbl", ".ini", ".xml"}:
        return "text"
    if magic in {"ELF", "PSP_ENCRYPTED", "SCE_ENCRYPTED"} or ext in {".prx", ".elf"}:
        return "executable"
    if magic == "AFS":
        return "archive"
    if ext in {".gmo", ".mdl", ".model"}:
        return "model"
    return "unknown"


def sha_extent(blob: mmap.mmap, start: int, size: int) -> str:
    digest = hashlib.sha256()
    end = start + size
    at = start
    while at < end:
        nxt = min(at + CHUNK, end)
        digest.update(blob[at:nxt])
        at = nxt
    return digest.hexdigest()


def safe_name(index: int, name: str) -> str:
    cleaned = name.replace("\\", "_").replace("/", "_").replace(":", "_")
    cleaned = cleaned.strip(". ") or "unnamed.bin"
    return f"{index:05d}_{cleaned}"


def inspect(path: Path, extract_dir: Path | None) -> tuple[dict, list[dict]]:
    with path.open("rb") as handle:
        blob = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            if blob[:4] != b"AFS\0":
                raise ValueError(f"{path}: not AFS")
            count = struct.unpack_from("<I", blob, 4)[0]
            table_end = 8 + count * ENTRY
            if table_end + 8 > len(blob):
                raise ValueError(f"{path}: entry table exceeds file")
            directory_offset, directory_size = struct.unpack_from("<II", blob, table_end)
            if directory_size != count * DIR_ENTRY:
                raise ValueError(
                    f"{path}: directory size {directory_size} != {count} * {DIR_ENTRY}"
                )
            if directory_offset + directory_size > len(blob):
                raise ValueError(f"{path}: directory exceeds file")

            rows = []
            previous_end = 0
            for index in range(count):
                offset, size = struct.unpack_from("<II", blob, 8 + index * ENTRY)
                if offset + size > len(blob):
                    raise ValueError(f"{path}: member {index} exceeds archive")
                if offset < previous_end:
                    raise ValueError(f"{path}: member {index} overlaps its predecessor")
                previous_end = offset + size
                directory = directory_offset + index * DIR_ENTRY
                name = decode_name(bytes(blob[directory:directory + 32]))
                head = bytes(blob[offset:offset + min(size, 32)])
                magic = magic_label(head)
                ext = Path(name).suffix.lower() or "<none>"
                row = {
                    "archive": path.name,
                    "index": index,
                    "name": name,
                    "extension": ext,
                    "offset": offset,
                    "size": size,
                    "allocated_to_next": (
                        directory_offset - offset
                        if index + 1 == count
                        else struct.unpack_from("<I", blob, 8 + (index + 1) * ENTRY)[0] - offset
                    ),
                    "magic": magic,
                    "category": classify(name, magic),
                    "sha256": sha_extent(blob, offset, size),
                    "head_hex": head.hex(" "),
                }
                rows.append(row)
                if extract_dir is not None:
                    extract_dir.mkdir(parents=True, exist_ok=True)
                    target = extract_dir / safe_name(index, name)
                    with target.open("wb") as out:
                        at = offset
                        end = offset + size
                        while at < end:
                            nxt = min(at + CHUNK, end)
                            out.write(blob[at:nxt])
                            at = nxt

            summary = {
                "archive": str(path.resolve()),
                "archive_size": len(blob),
                "member_count": count,
                "directory_offset": directory_offset,
                "directory_size": directory_size,
                "aligned_2048_members": sum(row["offset"] % 2048 == 0 for row in rows),
                "categories": dict(Counter(row["category"] for row in rows).most_common()),
                "extensions": dict(Counter(row["extension"] for row in rows).most_common()),
                "magics": dict(Counter(row["magic"] for row in rows).most_common()),
            }
            return summary, rows
        finally:
            blob.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("archives", nargs="+", type=Path)
    parser.add_argument("--extract", action="store_true")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    all_summaries = []
    all_rows = []
    for archive in args.archives:
        extract_dir = args.out_dir / "members" / archive.stem if args.extract else None
        summary, rows = inspect(archive, extract_dir)
        all_summaries.append(summary)
        all_rows.extend(rows)
        print(json.dumps(summary, ensure_ascii=False, indent=2))

    (args.out_dir / "afs_summary.json").write_text(
        json.dumps(all_summaries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.out_dir / "afs_inventory.json").write_text(
        json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (args.out_dir / "afs_inventory.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Produce an evidence-backed byte diff between a clean PSP ELF and a patch."""

from __future__ import annotations

import argparse
import hashlib
import json
import mmap
from pathlib import Path

from elftools.elf.elffile import ELFFile


MERGE_GAP = 64
BLOCK = 4096


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def exact_ranges(a: mmap.mmap, b: mmap.mmap) -> list[tuple[int, int]]:
    if len(a) != len(b):
        raise ValueError(f"length mismatch: {len(a)} != {len(b)}")
    ranges: list[tuple[int, int]] = []
    start = None
    for offset, (old, new) in enumerate(zip(a, b)):
        if old != new and start is None:
            start = offset
        elif old == new and start is not None:
            ranges.append((start, offset))
            start = None
    if start is not None:
        ranges.append((start, len(a)))
    return ranges


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not ranges:
        return []
    merged = [list(ranges[0])]
    for start, end in ranges[1:]:
        if start - merged[-1][1] <= MERGE_GAP:
            merged[-1][1] = end
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def section_map(path: Path) -> list[dict]:
    rows = []
    with path.open("rb") as handle:
        elf = ELFFile(handle)
        for section in elf.iter_sections():
            start = int(section["sh_offset"])
            size = int(section["sh_size"])
            rows.append(
                {
                    "name": section.name,
                    "type": str(section["sh_type"]),
                    "offset": start,
                    "end": start + size,
                    "size": size,
                    "address": int(section["sh_addr"]),
                }
            )
    return rows


def overlapping(sections: list[dict], start: int, end: int) -> list[str]:
    return [
        section["name"] or "<unnamed>"
        for section in sections
        if section["offset"] < end and section["end"] > start
    ]


def text_views(data: bytes) -> dict[str, str | None]:
    views: dict[str, str | None] = {}
    for codec in ("ascii", "cp932", "utf-8"):
        try:
            decoded = data.decode(codec)
        except UnicodeDecodeError:
            views[codec] = None
            continue
        rendered = "".join(ch if ch.isprintable() else f"\\x{ord(ch):02x}" for ch in decoded)
        views[codec] = rendered[:512]
    return views


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("patched", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sections = section_map(args.original)
    with args.original.open("rb") as fa, args.patched.open("rb") as fb:
        a = mmap.mmap(fa.fileno(), 0, access=mmap.ACCESS_READ)
        b = mmap.mmap(fb.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            exact = exact_ranges(a, b)
            merged = merge_ranges(exact)
            clusters = []
            for start, end in merged:
                old = bytes(a[start:end])
                new = bytes(b[start:end])
                changed = sum(x != y for x, y in zip(old, new))
                clusters.append(
                    {
                        "start": start,
                        "end": end,
                        "length": end - start,
                        "changed_bytes": changed,
                        "density": changed / (end - start),
                        "sections": overlapping(sections, start, end),
                        "original_sha256": sha(old),
                        "patched_sha256": sha(new),
                        "original_hex_head": old[:64].hex(" "),
                        "patched_hex_head": new[:64].hex(" "),
                        "original_text_head": text_views(old[:256]),
                        "patched_text_head": text_views(new[:256]),
                    }
                )

            blocks = []
            for start in range(0, len(a), BLOCK):
                end = min(start + BLOCK, len(a))
                changed = sum(x != y for x, y in zip(a[start:end], b[start:end]))
                if changed:
                    blocks.append(
                        {
                            "start": start,
                            "end": end,
                            "changed_bytes": changed,
                            "sections": overlapping(sections, start, end),
                        }
                    )

            report = {
                "original": str(args.original.resolve()),
                "patched": str(args.patched.resolve()),
                "size": len(a),
                "exact_range_count": len(exact),
                "merged_cluster_count": len(merged),
                "changed_bytes": sum(
                    sum(x != y for x, y in zip(a[start:end], b[start:end]))
                    for start, end in exact
                ),
                "sections": sections,
                "clusters": clusters,
                "changed_blocks": blocks,
            }
        finally:
            a.close()
            b.close()

    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {key: report[key] for key in ("size", "exact_range_count", "merged_cluster_count", "changed_bytes")},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

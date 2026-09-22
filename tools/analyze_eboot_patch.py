#!/usr/bin/env python3
"""Classify a fixed-layout PSP ELF patch into text and non-text changes."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from hanpatch.platforms.psp import eboot


JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff々〆ヶー]")


def decode(raw: bytes) -> str | None:
    try:
        return raw.decode("cp932")
    except UnicodeDecodeError:
        return None


def readable(text: str | None) -> bool:
    if not text:
        return False
    good = sum(ch.isprintable() or ch in "\r\n\t" for ch in text)
    return good / len(text) >= 0.92


def cells(blob: bytes):
    for lo, hi in eboot.data_ranges(blob):
        start = lo
        for pos in range(lo, hi):
            if blob[pos] != 0:
                continue
            if pos > start:
                yield start, pos, blob[start:pos]
            start = pos + 1


def c_string_at(blob: bytes, start: int, limit: int) -> bytes:
    end = blob.find(b"\0", start, limit)
    if end < 0:
        end = limit
    return blob[start:end]


def merge_offsets(offsets: list[int]) -> list[tuple[int, int]]:
    if not offsets:
        return []
    out = []
    start = previous = offsets[0]
    for offset in offsets[1:]:
        if offset != previous + 1:
            out.append((start, previous + 1))
            start = offset
        previous = offset
    out.append((start, previous + 1))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("patched", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    original = args.original.read_bytes()
    patched = args.patched.read_bytes()
    if len(original) != len(patched):
        raise SystemExit("ELFs must have identical lengths for fixed-slot analysis")

    changed_offsets = [i for i, (a, b) in enumerate(zip(original, patched)) if a != b]
    covered = bytearray(len(original))
    rows = []
    data_ranges = eboot.data_ranges(original)
    original_cells = list(cells(original))
    range_index = 0
    for index, (start, end, old_raw) in enumerate(original_cells):
        while range_index + 1 < len(data_ranges) and start >= data_ranges[range_index][1]:
            range_index += 1
        range_end = data_ranges[range_index][1]
        next_start = (
            original_cells[index + 1][0]
            if index + 1 < len(original_cells) and original_cells[index + 1][0] < range_end
            else range_end
        )
        new_raw = c_string_at(patched, start, next_start)
        if old_raw == new_raw:
            continue
        old_text = decode(old_raw)
        new_text = decode(new_raw)
        if not (readable(old_text) and readable(new_text)):
            continue
        covered_end = max(end, start + len(new_raw))
        for covered_index in range(start, covered_end):
            covered[covered_index] = 1
        rows.append(
            {
                "offset": start,
                "original_bytes": end - start,
                "patched_bytes": len(new_raw),
                "bytes_beyond_original_nul": max(0, len(new_raw) - (end - start)),
                "capacity_before_next_original_cell": next_start - start - 1,
                "overlaps_next_original_cell": start + len(new_raw) >= next_start,
                "original": old_text,
                "patched": new_text,
                "original_has_japanese": bool(JP.search(old_text or "")),
                "patched_has_japanese": bool(JP.search(new_text or "")),
                "patched_ascii_only": all(byte < 0x80 for byte in new_raw),
                "original_hex": old_raw.hex(" "),
                "patched_hex": new_raw.hex(" "),
            }
        )

    uncovered = [offset for offset in changed_offsets if not covered[offset]]
    uncovered_ranges = []
    for start, end in merge_offsets(uncovered):
        old = original[start:end]
        new = patched[start:end]
        uncovered_ranges.append(
            {
                "start": start,
                "end": end,
                "length": end - start,
                "original_hex": old[:128].hex(" "),
                "patched_hex": new[:128].hex(" "),
            }
        )

    json_path = args.out_dir / "eboot_changed_strings.json"
    csv_path = args.out_dir / "eboot_changed_strings.csv"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["offset"])
        writer.writeheader()
        writer.writerows(rows)
    (args.out_dir / "eboot_unclassified_changes.json").write_text(
        json.dumps(uncovered_ranges, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = {
        "changed_bytes": len(changed_offsets),
        "changed_text_slots": len(rows),
        "japanese_to_ascii_slots": sum(
            row["original_has_japanese"] and row["patched_ascii_only"] for row in rows
        ),
        "changed_bytes_covered_by_text_slots": len(changed_offsets) - len(uncovered),
        "unclassified_changed_bytes": len(uncovered),
        "unclassified_exact_ranges": len(uncovered_ranges),
    }
    (args.out_dir / "eboot_patch_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Collect the game's character-index table for the font.

The game stores its text as pairs of bytes >= 0x80 and asks the font for
``((b0 - 0x80) << 7) + (b1 - 0x80) + 0x100`` (the patch moved the old 0xAC00
base down to 0x0100).  Korean is re-encoded so a syllable's index is
``codepoint - 0xAC00``; the original Japanese text keeps its own indices.

This walks every source string we know about and records which index means
which character, so the font can carry a glyph for the original text too.

Sources:
  * ``work/**/*.input.jsonl`` - ``source_raw_hex`` is the literal bytes.
  * the translation workbook - ``source_jp`` re-encoded to CP932, but only for
    rows whose ``evidence`` says the string was really found (the
    ``printable_cp932_candidate`` rows are random bytes that happen to print).
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
from pathlib import Path

# Evidence values that mean "this really is a string in the game data".
REAL_EVIDENCE = {
    "direct_32bit_pointer",
    "nul_terminated_cp932_with_kana",
    "fan_patch_modified",
}

APPLIED_STATUSES = {"translated", "approved"}


def index_of(high: int, low: int) -> int:
    return ((high - 0x80) << 7) + (low - 0x80)


def walk(raw: bytes) -> list[tuple[int, str]]:
    """[(index, character), ...] for one stored string."""
    pairs: list[tuple[int, str]] = []
    cursor = 0
    while cursor < len(raw):
        byte = raw[cursor]
        if byte < 0x80:
            cursor += 1
            continue
        if cursor + 1 >= len(raw):
            break
        try:
            char = raw[cursor : cursor + 2].decode("cp932")
        except UnicodeDecodeError:
            cursor += 2
            continue
        if len(char) == 1:
            pairs.append((index_of(byte, raw[cursor + 1]), char))
        cursor += 2
    return pairs


def add(pairs: list[tuple[int, str]], jp: dict[int, str], counts: dict[int, int]) -> int:
    seen = 0
    for index, char in pairs:
        jp.setdefault(index, char)
        counts[index] = counts.get(index, 0) + 1
        seen += 1
    return seen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--workbook", type=Path,
                        default=Path("work/text/translations_next_plus_development_v9_2026-09-26.csv"),
                        help="rows still untranslated in this workbook need original-text glyphs")
    parser.add_argument("--all-rows", action="store_true",
                        help="use every row, not just the untranslated ones")
    args = parser.parse_args()
    root = args.root

    jp: dict[int, str] = {}
    counts: dict[int, int] = {}
    from_raw = 0
    from_workbook = 0

    if args.all_rows:
        for path in sorted(glob.glob(str(root / "work/**/*.input.jsonl"), recursive=True)):
            for line in Path(path).read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                hexed = record.get("source_raw_hex")
                if not hexed:
                    continue
                raw = bytes.fromhex("".join(hexed.split()))
                from_raw += add(walk(raw), jp, counts)

        for path in sorted(glob.glob(str(root / "work/text/*.csv"))):
            with open(path, encoding="utf-8-sig", newline="") as handle:
                try:
                    rows = list(csv.DictReader(handle))
                except (csv.Error, UnicodeDecodeError):
                    continue
            for row in rows:
                if (row.get("evidence") or "") not in REAL_EVIDENCE:
                    continue
                try:
                    raw = (row.get("source_jp") or "").encode("cp932")
                except UnicodeEncodeError:
                    continue
                from_workbook += add(walk(raw), jp, counts)

    # Only rows that stayed untranslated still show the original characters, so
    # only they justify shipping original-text glyphs (and only they set the
    # frequency order used to trim the set to the font's size budget).
    workbook = root / args.workbook
    if workbook.is_file():
        with workbook.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if not args.all_rows and row["status"] in APPLIED_STATUSES:
                    continue
                if not args.all_rows and (row.get("evidence") or "") not in REAL_EVIDENCE:
                    continue
                try:
                    raw = (row.get("source_jp") or "").encode("cp932")
                except UnicodeEncodeError:
                    continue
                from_workbook += add(walk(raw), jp, counts)

    # Korean syllables claim their own index, and they win any collision.
    korean: set[int] = set()
    syllables: set[str] = set()
    for path in sorted(glob.glob(str(root / "work/**/*.jsonl"), recursive=True)):
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            for char in json.loads(line).get("target_ko") or "":
                if 0xAC00 <= ord(char) <= 0xD7A3:
                    korean.add(ord(char) - 0xAC00)
                    syllables.add(char)
    for path in sorted(glob.glob(str(root / "work/text/*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as handle:
            try:
                rows = list(csv.DictReader(handle))
            except (csv.Error, UnicodeDecodeError):
                continue
        for row in rows:
            for char in row.get("target_ko") or "":
                if 0xAC00 <= ord(char) <= 0xD7A3:
                    korean.add(ord(char) - 0xAC00)
                    syllables.add(char)

    collisions = sorted(korean & set(jp))
    wanted = {index: char for index, char in sorted(jp.items()) if index not in korean}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    order = sorted(wanted, key=lambda index: (-counts.get(index, 0), index))
    args.output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "note": "index -> original character, most used first; Korean wins collisions",
                "jp": {str(index): wanted[index] for index in order},
                "freq": {str(index): counts.get(index, 0) for index in order},
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )

    report = {
        "output": str(args.output),
        "jp_indices_total": len(jp),
        "jp_glyphs_available": len(wanted),
        "korean_indices": len(korean),
        "korean_syllables": len(syllables),
        "collisions_korean_wins": len(collisions),
        "collision_indices": collisions,
        "observations_from_raw_hex": from_raw,
        "observations_from_workbook": from_workbook,
    }
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "collision_indices"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

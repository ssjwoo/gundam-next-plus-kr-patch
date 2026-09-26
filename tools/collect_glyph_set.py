#!/usr/bin/env python3
"""Collect the code points the game needs glyphs for.

The replaced decoder returns ASCII unchanged and Korean syllables at their own
Unicode code points, so the font only needs those two sets.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path,
                        default=ROOT / "work/text/translations_next_plus_development_v9_2026-09-26.csv")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "work/font_glyph_set_2026-09-26.txt")
    args = parser.parse_args()

    chars: set[str] = set(chr(c) for c in range(0x20, 0x7F))

    with args.workbook.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["status"] == "translated":
                chars.update(row.get("target_ko") or "")

    for name, key in (
        ("work/next_plus_mission_response_v3/merged.response.jsonl", "target_ko"),
        ("work/next_plus_map_remaining_handoff_v1/remaining.response.jsonl", "target_ko"),
        ("work/next_plus_map_candidates_v2/map_candidate.response.jsonl", "target_ko"),
    ):
        path = ROOT / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                chars.update(json.loads(line).get(key) or "")

    hangul = {c for c in chars if "\uac00" <= c <= "\ud7a3"}
    ascii_chars = {c for c in chars if ord(c) < 0x80}
    others = chars - hangul - ascii_chars

    out = args.output
    out.write_text("".join(sorted(hangul | ascii_chars)), encoding="utf-8")
    print(json.dumps({
        "total": len(hangul | ascii_chars),
        "hangul": len(hangul),
        "ascii": len(ascii_chars),
        "excluded_non_encodable": len(others),
        "output": str(out),
    }, ensure_ascii=False, indent=2))
    if others:
        print("excluded:", "".join(sorted(others))[:80])


if __name__ == "__main__":
    main()

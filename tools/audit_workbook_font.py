#!/usr/bin/env python3
"""Check compact PGF coverage for recovered slot text without running the game.

Glyph-record equality is byte evidence, not a verdict on drawn text or layout.
Only revision-2 PGFs without shadow glyphs are supported by this audit.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import struct
from pathlib import Path

from make_hangul_poc import RUNTIME_INDEX_GLYPHS, encode_hangul


def bits(data: bytes, count: int, position: int) -> int:
    if not 0 < count <= 32 or position < 0 or position + count > len(data) * 8:
        raise ValueError("PGF bitfield exceeds table bounds")
    value = int.from_bytes(data[position // 8:(position + count + 7) // 8], "little")
    return (value >> (position & 7)) & ((1 << count) - 1)


def font_records(path: Path) -> tuple[dict[int, bytes], dict]:
    data = path.read_bytes()
    if len(data) < 392 or data[4:8] != b"PGF0":
        raise ValueError("Not a complete PGF font")
    header_size = struct.unpack_from("<H", data, 2)[0]
    revision, _, map_len, glyphs, map_bpe, pointer_bpe = struct.unpack_from("<6i", data, 8)
    first, last = struct.unpack_from("<HH", data, 182)
    dim, x, y, advance = struct.unpack_from("<4B", data, 258)
    shadow_len = struct.unpack_from("<i", data, 364)[0]
    if revision != 2 or shadow_len or header_size < 392:
        raise ValueError("Audit supports revision 2 without shadow glyphs only")
    if map_len <= 0 or glyphs <= 0 or last - first + 1 != map_len:
        raise ValueError("Invalid PGF glyph/map dimensions")
    if not 0 < map_bpe <= 32 or not 0 < pointer_bpe <= 32:
        raise ValueError("Invalid PGF map/pointer bit width")
    cursor = header_size + (dim + x + y + advance) * 8
    metric_tables = data[header_size:cursor]
    map_size = math.ceil(map_len * map_bpe / 32) * 4
    charmap = data[cursor:cursor + map_size]
    cursor += map_size
    pointer_size = math.ceil(glyphs * pointer_bpe / 32) * 4
    pointers = data[cursor:cursor + pointer_size]
    cursor += pointer_size
    glyph_data = data[cursor:]
    if len(charmap) != map_size or len(pointers) != pointer_size:
        raise ValueError("Truncated PGF tables")
    records = {}
    for index in range(map_len):
        glyph = bits(charmap, map_bpe, index * map_bpe)
        if glyph >= glyphs:
            continue
        position = bits(pointers, pointer_bpe, glyph * pointer_bpe) * 4
        size = bits(glyph_data, 14, position * 8)
        if size < 2 or position + size > len(glyph_data):
            raise ValueError(f"Truncated PGF glyph {glyph}")
        records[first + index] = glyph_data[position:position + size]
    return records, {"path": str(path.resolve()), "bytes": len(data), "glyphs": glyphs,
                     "mapped_codes": len(records), "sha256": hashlib.sha256(data).hexdigest(),
                     "metric_tables_sha256": hashlib.sha256(metric_tables).hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("translations_csv", type=Path)
    parser.add_argument("provided_font", type=Path)
    parser.add_argument("baseline_font", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--hangul-base", type=lambda value: int(value, 0), default=0x100)
    args = parser.parse_args()
    with args.translations_csv.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = set()
    for row in rows:
        if row["status"] not in {"translated", "approved"}:
            continue
        raw = encode_hangul(row["target_ko"])
        pos = 0
        while pos < len(raw):
            lead = raw[pos]
            if lead < 0x80:
                if lead >= 0x20:
                    required.add(lead)
                pos += 1
            else:
                required.add(args.hangul_base + ((lead - 0x80) << 7) + raw[pos + 1] - 0x80)
                pos += 2
    provided, provided_info = font_records(args.provided_font)
    baseline, baseline_info = font_records(args.baseline_font)
    changed = sorted(code for code in provided.keys() & baseline.keys() if provided[code] != baseline[code])
    runtime_codes = {args.hangul_base + index: glyph for index, glyph in RUNTIME_INDEX_GLYPHS.items()}
    missing = sorted(required - provided.keys())
    report = {
        "workbook": str(args.translations_csv.resolve()), "rows": len(rows),
        "provided_font": provided_info, "baseline_font": baseline_info,
        "hangul_base": args.hangul_base, "required_workbook_codes": len(required),
        "missing_workbook_codes": missing,
        "added_codes": sorted(provided.keys() - baseline.keys()),
        "removed_codes": sorted(baseline.keys() - provided.keys()),
        "changed_common_glyph_record_codes": changed,
        "changed_records_required_by_workbook": sorted(required & set(changed)),
        "metric_tables_equal": provided_info["metric_tables_sha256"] == baseline_info["metric_tables_sha256"],
        "missing_runtime_digit_or_trademark_codes": {str(code): char for code, char in runtime_codes.items() if code not in provided},
        "runtime_verdict": "NOT_TESTED",
        "scope": "PGF map/record byte audit for recovered text and known runtime codes; not full game/font/layout validation",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value if not isinstance(value, list) else len(value)
                      for key, value in report.items() if key not in {"provided_font", "baseline_font"}}, ensure_ascii=True, indent=2))
    if missing or report["missing_runtime_digit_or_trademark_codes"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

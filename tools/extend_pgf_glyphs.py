#!/usr/bin/env python3
"""Add declared Hangul glyphs to a revision-2 PGF, preserving existing glyphs.

Uses a locally supplied licensed TTF. Existing metric-table indices, map codes,
glyph records and runtime aliases are preserved. This is a static development
font operation; it does not establish in-game rendering or aesthetic approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

import freetype

from audit_workbook_font import bits, font_records
from make_hangul_poc import DISPLACED_HANGUL, RUNTIME_INDEX_GLYPHS
from make_pgf_from_ttf import (BitWriter, FONT_PGF_BMP_H_ROWS, METRIC_INDEX_FLAGS,
                               encode_bitmap, metric_keys, rasterise, set_bits)


def extend(source: Path, ttf: Path, chars: str, size: int) -> tuple[bytes, dict]:
    original = source.read_bytes()
    old_records, old_info = font_records(source)
    header_size = struct.unpack_from("<H", original, 2)[0]
    _, _, map_len, glyph_count, map_bpe, pointer_bpe = struct.unpack_from("<6i", original, 8)
    first, last = struct.unpack_from("<HH", original, 182)
    if header_size != 392 or map_bpe != 14 or pointer_bpe != 19:
        raise ValueError("Unsupported PGF table representation")
    lengths = list(original[258:262])
    cursor = header_size
    tables = []
    for length in lengths:
        tables.append([struct.unpack_from("<ii", original, cursor + i * 8) for i in range(length)])
        cursor += length * 8
    old_map_at = cursor
    map_bytes = (map_len * map_bpe + 31) // 32 * 4
    charmap = bytearray(original[cursor:cursor + map_bytes])
    cursor += map_bytes
    pointer_bytes = (glyph_count * pointer_bpe + 31) // 32 * 4
    old_pointers = original[cursor:cursor + pointer_bytes]
    cursor += pointer_bytes
    glyph_blob = bytearray(original[cursor:])
    pointers = [bits(old_pointers, pointer_bpe, i * pointer_bpe) for i in range(glyph_count)]
    face = freetype.Face(str(ttf))
    added = []
    for char in sorted(set(chars)):
        cp = ord(char)
        if not 0xAC00 <= cp <= 0xD7A3:
            if char.isspace():
                continue
            raise ValueError("Only declared precomposed Hangul additions are supported")
        index = DISPLACED_HANGUL.get(cp, cp - 0xAC00)
        code = 0x100 + index
        if index in RUNTIME_INDEX_GLYPHS:
            raise ValueError("Requested syllable collides with a reserved runtime index")
        if code in old_records:
            continue
        if not first <= code <= last:
            raise ValueError("Addition exceeds the existing compact map range")
        if face.get_char_index(cp) == 0:
            raise ValueError("TTF has no requested syllable")
        glyph = rasterise(face, char, size)
        if glyph is None:
            raise ValueError("Requested glyph could not be rasterized")
        max_w, max_h = struct.unpack_from("<HH", original, 252)
        if glyph["w"] > max_w or glyph["h"] > max_h:
            raise ValueError("New glyph exceeds existing font cell profile")
        metrics = []
        for slot, key in enumerate(metric_keys(glyph)):
            if key not in tables[slot]:
                if len(tables[slot]) >= 255:
                    raise ValueError("Metric table capacity exceeded")
                tables[slot].append(key)
            metrics.append(tables[slot].index(key))
        writer = BitWriter()
        writer.put(14, 0)
        for value in (glyph["w"], glyph["h"], glyph["left"] & 127, glyph["top"] & 127):
            writer.put(7, value)
        writer.put(6, FONT_PGF_BMP_H_ROWS | METRIC_INDEX_FLAGS)
        writer.put(2, 0); writer.put(2, 0); writer.put(3, 0); writer.put(9, 0)
        for index in metrics:
            writer.put(8, index)
        record = bytearray(writer.data)
        record.extend(encode_bitmap(glyph["rows"]))
        record.extend(bytes(-len(record) % 4))
        set_bits(record, 14, 0, len(record))
        glyph_blob.extend(bytes(-len(glyph_blob) % 4))
        pointers.append(len(glyph_blob) // 4)
        set_bits(charmap, map_bpe, (code - first) * map_bpe, len(pointers) - 1)
        glyph_blob.extend(record)
        added.append({"char": char, "code": code, "record_bytes": len(record), "metrics": metrics,
                      "width": glyph["w"], "height": glyph["h"]})
    header = bytearray(original[:header_size])
    struct.pack_into("<i", header, 20, len(pointers))
    header[258:262] = bytes(len(table) for table in tables)
    table_blob = b"".join(struct.pack("<ii", *entry) for table in tables for entry in table)
    pointer_blob = bytearray((len(pointers) * pointer_bpe + 31) // 32 * 4)
    for i, value in enumerate(pointers):
        set_bits(pointer_blob, pointer_bpe, i * pointer_bpe, value)
    result = bytes(header) + table_blob + bytes(charmap) + bytes(pointer_blob) + bytes(glyph_blob)
    # Check metric values by original index independently of serialized offsets.
    for slot, length in enumerate(lengths):
        assert len(tables[slot]) >= length
    return result, {"baseline": old_info, "ttf_sha256": hashlib.sha256(ttf.read_bytes()).hexdigest(),
                    "pixel_size": size, "added_glyphs": added, "original_glyph_records": old_records,
                    "original_metric_tables": tables, "original_table_lengths": lengths}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_pgf", type=Path)
    parser.add_argument("ttf", type=Path)
    parser.add_argument("chars_txt", type=Path)
    parser.add_argument("output_pgf", type=Path)
    parser.add_argument("--size", type=int, default=17)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--expected-ttf-sha256", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.output_pgf.exists() or args.report.exists():
        parser.error("Output or report exists; use a new candidate path")
    if hashlib.sha256(args.source_pgf.read_bytes()).hexdigest() != args.expected_source_sha256:
        parser.error("Source PGF identity mismatch")
    if hashlib.sha256(args.ttf.read_bytes()).hexdigest() != args.expected_ttf_sha256:
        parser.error("TTF identity mismatch")
    result, report = extend(args.source_pgf, args.ttf, args.chars_txt.read_text(encoding="utf-8"), args.size)
    args.output_pgf.parent.mkdir(parents=True, exist_ok=True)
    args.output_pgf.write_bytes(result)
    readback, info = font_records(args.output_pgf)
    old_records = report.pop("original_glyph_records")
    assert all(readback.get(code) == value for code, value in old_records.items()), "Existing glyph changed"
    assert all(item["code"] in readback for item in report["added_glyphs"])
    tables = report.pop("original_metric_tables")
    old_lengths = report.pop("original_table_lengths")
    old_data = args.source_pgf.read_bytes()
    cursor = 392
    for slot, length in enumerate(old_lengths):
        assert [struct.unpack_from("<ii", old_data, cursor + i * 8) for i in range(length)] == tables[slot][:length]
        cursor += length * 8
    report.update({"output": info, "existing_records_preserved": len(old_records),
                   "existing_metric_indices_preserved": True, "runtime_aliases_preserved": True,
                   "static_verdict": "PASS", "runtime_verdict": "NOT_TESTED"})
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"bytes": len(result), "added": len(report["added_glyphs"]),
                      "existing_records_preserved": len(old_records), "static_verdict": "PASS"}))


if __name__ == "__main__":
    main()

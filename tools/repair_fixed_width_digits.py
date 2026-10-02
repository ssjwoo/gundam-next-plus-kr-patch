#!/usr/bin/env python3
"""Repair the supplied 2026-10-02 patch's fixed-width digit table and PGF map.

Keep the supplied font's existing glyph records and metrics. Reuse its ASCII
digit glyphs for the ten reserved runtime codes. No emulator or ISO is launched.
This deliberately accepts only the exact audited input artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from audit_workbook_font import bits, font_records
from recover_source_workbook import SOURCE_SHA256


PROVIDED_ELF_SHA256 = "e671072f042f8f166b46f80e08612d0e066187ee90f739e6223251934f0df045"
PROVIDED_FONT_SHA256 = "475435e283c078425512863b2470d6f1de442e4badb54598943421fd559f1378"
DIGIT_TABLE_OFFSET = 0x28D3B4
DIGIT_TABLE_BYTES = bytes.fromhex("824f825082518252825382548255825682578258")
PROVIDED_DIGIT_BYTES = b"0123456789" + bytes(10)
RUNTIME_DIGIT_FIRST_CODE = 0x100 + 207


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def set_bits(buffer: bytearray, count: int, position: int, value: int) -> None:
    if not 0 <= value < (1 << count) or position < 0 or position + count > len(buffer) * 8:
        raise ValueError("Font map update exceeds verified bounds")
    for index in range(count):
        target = position + index
        mask = 1 << (target & 7)
        if value & (1 << index):
            buffer[target // 8] |= mask
        else:
            buffer[target // 8] &= ~mask


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_elf", type=Path)
    parser.add_argument("provided_elf", type=Path)
    parser.add_argument("provided_font", type=Path)
    parser.add_argument("outdir", type=Path)
    args = parser.parse_args()
    if args.outdir.exists():
        parser.error(f"Output directory already exists: {args.outdir}")
    original = args.original_elf.read_bytes()
    elf = args.provided_elf.read_bytes()
    font = args.provided_font.read_bytes()
    for name, data, expected in (("original ELF", original, SOURCE_SHA256),
                                 ("provided ELF", elf, PROVIDED_ELF_SHA256),
                                 ("provided font", font, PROVIDED_FONT_SHA256)):
        if sha256(data) != expected:
            parser.error(f"Wrong {name}; recovery inputs require re-audit")
    offset, end = DIGIT_TABLE_OFFSET, DIGIT_TABLE_OFFSET + len(DIGIT_TABLE_BYTES)
    if original[offset:end] != DIGIT_TABLE_BYTES or elf[offset:end] != PROVIDED_DIGIT_BYTES:
        parser.error("Digit table bytes differ from the verified regression")
    before_records, _ = font_records(args.provided_font)
    first = struct.unpack_from("<H", font, 182)[0]
    map_len, glyph_count, map_bpe = struct.unpack_from("<3i", font, 16)
    header_size = struct.unpack_from("<H", font, 2)[0]
    metric_lengths = struct.unpack_from("<4B", font, 258)
    map_offset = header_size + sum(metric_lengths) * 8
    map_bytes = ((map_len * map_bpe + 31) // 32) * 4
    old_map = font[map_offset:map_offset + map_bytes]
    updated_font = bytearray(font)
    aliases = []
    for digit in range(10):
        ascii_code = ord(str(digit))
        runtime_code = RUNTIME_DIGIT_FIRST_CODE + digit
        if ascii_code not in before_records or not 0 <= runtime_code - first < map_len:
            parser.error("Required ASCII/runtime digit lies outside verified font coverage")
        glyph = bits(old_map, map_bpe, (ascii_code - first) * map_bpe)
        if glyph >= glyph_count:
            parser.error("Missing ASCII digit glyph")
        set_bits(updated_font, map_bpe, map_offset * 8 + (runtime_code - first) * map_bpe, glyph)
        aliases.append({"digit": digit, "runtime_code": runtime_code, "ascii_code": ascii_code,
                        "glyph_index": glyph})
    updated_elf = bytearray(elf)
    updated_elf[offset:end] = DIGIT_TABLE_BYTES
    if updated_elf[:offset] != elf[:offset] or updated_elf[end:] != elf[end:]:
        raise AssertionError("ELF changes escaped the digit table")
    if updated_font[:map_offset] != font[:map_offset] or updated_font[map_offset + map_bytes:] != font[map_offset + map_bytes:]:
        raise AssertionError("PGF changes escaped the character map")
    args.outdir.mkdir(parents=True, exist_ok=False)
    elf_path, font_path = args.outdir / "digit_fixed.elf", args.outdir / "digit_fixed.pgf"
    elf_path.write_bytes(updated_elf)
    font_path.write_bytes(updated_font)
    after_records, _ = font_records(font_path)
    runtime_codes = {row["runtime_code"] for row in aliases}
    for code, record in before_records.items():
        if code not in runtime_codes and after_records.get(code) != record:
            raise AssertionError(f"Unrelated glyph mapping changed at {code:#x}")
    for row in aliases:
        if after_records[row["runtime_code"]] != after_records[row["ascii_code"]]:
            raise AssertionError("Runtime digit does not read back as its existing ASCII glyph")
    report = {
        "provided_elf_sha256": sha256(elf), "provided_font_sha256": sha256(font),
        "output_elf": str(elf_path.resolve()), "output_font": str(font_path.resolve()),
        "output_elf_sha256": sha256(updated_elf), "output_font_sha256": sha256(updated_font),
        "elf_changed_bytes": sum(a != b for a, b in zip(elf, updated_elf)),
        "font_changed_bytes": sum(a != b for a, b in zip(font, updated_font)),
        "font_size_unchanged": len(font) == len(updated_font),
        "digit_table_offset": hex(offset), "digit_table_hex": DIGIT_TABLE_BYTES.hex(),
        "aliases": aliases, "other_glyph_records_unchanged": True,
        "static_verdict": "PASS", "runtime_verdict": "NOT_TESTED",
    }
    (args.outdir / "repair_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Inspect PSP PGF metadata and character-map coverage."""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path


def get_bits(data: bytes, bit_count: int, bit_pos: int) -> int:
    value = int.from_bytes(data[bit_pos // 8 : bit_pos // 8 + 8], "little")
    return (value >> (bit_pos & 7)) & ((1 << bit_count) - 1)


def parse(path: Path) -> dict:
    data = path.read_bytes()
    if data[4:8] != b"PGF0":
        raise ValueError(f"{path} is not a PGF font")

    header_size = struct.unpack_from("<H", data, 2)[0]
    revision, version, map_len, pointer_len, map_bpe, pointer_bpe = struct.unpack_from(
        "<6i", data, 8
    )
    first_glyph, last_glyph = struct.unpack_from("<HH", data, 182)
    dim_len, x_len, y_len, advance_len = struct.unpack_from("<4B", data, 258)
    shadow_len, shadow_bpe = struct.unpack_from("<ii", data, 364)
    cursor = header_size
    cursor += (dim_len + x_len + y_len + advance_len) * 8
    cursor += math.ceil(shadow_len * shadow_bpe / 32) * 4
    if revision == 3:
        comp1, comp2 = struct.unpack_from("<ii", data, 392)
        cursor += 20 + (comp1 + comp2) * 4
    charmap_size = math.ceil(map_len * map_bpe / 32) * 4
    charmap = data[cursor : cursor + charmap_size]

    def glyph_index(codepoint: int) -> int | None:
        index = codepoint - first_glyph
        if not 0 <= index < map_len:
            return None
        value = get_bits(charmap, map_bpe, index * map_bpe)
        return None if value >= pointer_len else value

    probes = {}
    for char in "Aあ亜가각힣▼▲▽↓":
        codepoint = ord(char)
        probes[f"U+{codepoint:04X} {char}"] = glyph_index(codepoint)
    for encoded in (0x82A0, 0xB0A1):
        probes[f"raw-0x{encoded:04X}"] = glyph_index(encoded)

    hangul_present = 0
    for codepoint in range(0xAC00, 0xD7A4):
        if glyph_index(codepoint) is not None:
            hangul_present += 1

    return {
        "path": str(path),
        "size": len(data),
        "revision": revision,
        "version": version,
        "font_name": data[53:117].split(b"\0", 1)[0].decode("ascii", "replace"),
        "font_type": data[117:181].split(b"\0", 1)[0].decode("ascii", "replace"),
        "first_glyph": first_glyph,
        "last_glyph": last_glyph,
        "charmap_length": map_len,
        "char_pointer_length": pointer_len,
        "charmap_bpe": map_bpe,
        "char_pointer_bpe": pointer_bpe,
        "hangul_syllables_present": hangul_present,
        "hangul_syllables_total": 0xD7A4 - 0xAC00,
        "probes": probes,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("fonts", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = [parse(path) for path in args.fonts]
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()

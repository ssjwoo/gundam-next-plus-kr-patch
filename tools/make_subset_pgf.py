#!/usr/bin/env python3
"""Build a small PGF from a source PGF, keeping only the glyphs the patch needs.

The replaced decoder returns ASCII unchanged and Korean syllables at
``BASE + (codepoint - 0xAC00)``, so the output font maps:

  * 0x20..0x7E            -> the source font's ASCII glyphs
  * BASE + idx (hangul)   -> the source font's glyph for U+AC00+idx

Only the header, the fixed metric tables and the glyph records are carried
over; the character map and the glyph pointer table are rebuilt.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

HEADER_SIZE = 392          # revision 2 header
MAP_BPE = 14               # matches stock fonts; big enough for the whole span


def get_bits(data: bytes, count: int, position: int) -> int:
    value = int.from_bytes(data[position // 8 : position // 8 + 8], "little")
    return (value >> (position & 7)) & ((1 << count) - 1)


def set_bits(buf: bytearray, count: int, position: int, value: int) -> None:
    for index in range(count):
        bit = (value >> index) & 1
        absolute = position + index
        byte = absolute // 8
        mask = 1 << (absolute & 7)
        if bit:
            buf[byte] |= mask
        else:
            buf[byte] &= ~mask & 0xFF


def align32(size: int) -> int:
    return (size + 31) & ~31


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--chars", type=Path, required=True,
                        help="UTF-8 text file with the characters to keep")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hangul-base", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    data = args.source.read_bytes()
    if data[4:8] != b"PGF0":
        raise SystemExit("source is not a PGF font")
    header_size = struct.unpack_from("<H", data, 2)[0]
    revision, version = struct.unpack_from("<ii", data, 8)
    map_len, ptr_len, map_bpe, ptr_bpe = struct.unpack_from("<4i", data, 16)
    first_glyph, last_glyph = struct.unpack_from("<HH", data, 182)
    dim_len, x_len, y_len, adv_len = struct.unpack_from("<4B", data, 258)
    shadow_len, shadow_bpe = struct.unpack_from("<2i", data, 364)
    if revision != 2:
        raise SystemExit(f"only revision 2 sources are supported, got {revision}")
    if shadow_len:
        raise SystemExit("source uses shadow glyphs; strip them first")

    cursor = header_size
    tables_size = (dim_len + x_len + y_len + adv_len) * 8
    tables = data[cursor : cursor + tables_size]
    cursor += tables_size
    shadow_size = align32(shadow_len * shadow_bpe) // 8
    cursor += shadow_size
    map_size = align32(map_len * map_bpe) // 8
    charmap = data[cursor : cursor + map_size]
    cursor += map_size
    ptr_size = align32(ptr_len * ptr_bpe) // 8
    charptr = data[cursor : cursor + ptr_size]
    cursor += ptr_size
    glyph_data = data[cursor:]

    old_map: dict[int, int] = {}
    for index in range(map_len):
        value = get_bits(charmap, map_bpe, index * map_bpe)
        if value < ptr_len:
            old_map[first_glyph + index] = value

    def old_ptr(glyph: int) -> int:
        return get_bits(charptr, ptr_bpe, glyph * ptr_bpe)

    chars = args.chars.read_text(encoding="utf-8")
    wanted: list[tuple[int, int]] = []      # (new codepoint, old glyph index)
    for char in sorted(set(chars)):
        codepoint = ord(char)
        if codepoint < 0x80:
            new_cp, old_cp = codepoint, codepoint
        elif 0xAC00 <= codepoint <= 0xD7A3:
            new_cp, old_cp = args.hangul_base + (codepoint - 0xAC00), codepoint
        else:
            new_cp, old_cp = codepoint, codepoint
        glyph = old_map.get(old_cp)
        if glyph is None:
            continue
        wanted.append((new_cp, glyph))
    if not wanted:
        raise SystemExit("no glyphs selected")

    wanted.sort()
    new_first = wanted[0][0]
    new_last = wanted[-1][0]
    new_map_len = new_last - new_first + 1
    if new_map_len > (1 << MAP_BPE):
        raise SystemExit("character map does not fit in the chosen bpe")

    # Copy glyph records, aligning each to 4 bytes (the pointer is in 4-byte units).
    glyph_blob = bytearray()
    offsets: dict[int, int] = {}      # old glyph index -> data offset in 4-byte units
    order: list[int] = []             # new glyph index -> old glyph index
    for _, old_glyph in wanted:
        if old_glyph in offsets:
            continue
        pointer = old_ptr(old_glyph) * 4
        record_size = get_bits(glyph_data, 14, pointer * 8)
        if not record_size:
            raise SystemExit(f"glyph {old_glyph} has zero size")
        while len(glyph_blob) % 4:
            glyph_blob.append(0)
        offsets[old_glyph] = len(glyph_blob) // 4
        order.append(old_glyph)
        glyph_blob += glyph_data[pointer : pointer + record_size]

    new_glyph_count = len(order)
    sentinel = (1 << MAP_BPE) - 1
    if sentinel < new_glyph_count:
        raise SystemExit("not enough bpe headroom for the missing-glyph value")

    new_charmap = bytearray(align32(new_map_len * MAP_BPE) // 8)
    for new_cp, old_glyph in wanted:
        new_index = order.index(old_glyph)
        set_bits(new_charmap, MAP_BPE, (new_cp - new_first) * MAP_BPE, new_index)

    new_ptr = bytearray(align32(new_glyph_count * ptr_bpe) // 8)
    for index, old_glyph in enumerate(order):
        set_bits(new_ptr, ptr_bpe, index * ptr_bpe, offsets[old_glyph])

    header = bytearray(data[:header_size])
    struct.pack_into("<i", header, 16, new_map_len)
    struct.pack_into("<i", header, 20, new_glyph_count)
    struct.pack_into("<i", header, 24, MAP_BPE)
    struct.pack_into("<i", header, 28, ptr_bpe)
    struct.pack_into("<H", header, 182, new_first)
    struct.pack_into("<H", header, 184, new_last)

    out = bytes(header) + tables + bytes(new_charmap) + bytes(new_ptr) + bytes(glyph_blob)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(out)

    report = {
        "source": str(args.source),
        "source_bytes": len(data),
        "output": str(args.output),
        "output_bytes": len(out),
        "glyphs": new_glyph_count,
        "codepoints": len(wanted),
        "first_codepoint": f"{new_first:#06x}",
        "last_codepoint": f"{new_last:#06x}",
        "map_bpe": MAP_BPE,
        "hangul_base": f"{args.hangul_base:#06x}",
        "version": version,
    }
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

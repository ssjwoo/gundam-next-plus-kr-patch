#!/usr/bin/env python3
"""Rasterise a freely licensed font into a PGF the patch can load.

The patch's decoder returns ASCII unchanged and Korean syllables at
``HANGUL_BASE + (codepoint - 0xAC00)``, so the character map is written with
those code points directly.

Glyph metrics use the same shape real firmware fonts use: four tables
(dimension, x adjust, y adjust, advance) referenced by an 8-bit index, with the
corresponding flag bits set.  Bitmaps are plain 4bpp nibble RLE where each group
of up to eight pixels is a literal run (nibble 16-k, then k nibbles).
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

import freetype

HEADER_SIZE = 392
MAP_BPE = 14
PTR_BPE = 19
BPP = 4

FONT_PGF_BMP_H_ROWS = 0x01
METRIC_INDEX_FLAGS = 0x04 | 0x08 | 0x10 | 0x20
HANGUL_BASE = 0x0100
MARKER_CODEPOINT = 0x25BC
MAX_TABLE_ENTRIES = 255


def build_header(metrics: dict, map_len: int, ptr_len: int, first: int, last: int,
                 table_lengths: tuple[int, int, int, int]) -> bytearray:
    header = bytearray(HEADER_SIZE)
    struct.pack_into("<H", header, 0, 0)
    struct.pack_into("<H", header, 2, HEADER_SIZE)
    header[4:8] = b"PGF0"
    struct.pack_into("<i", header, 8, 2)
    struct.pack_into("<i", header, 12, 6)
    struct.pack_into("<i", header, 16, map_len)
    struct.pack_into("<i", header, 20, ptr_len)
    struct.pack_into("<i", header, 24, MAP_BPE)
    struct.pack_into("<i", header, 28, PTR_BPE)
    header[34] = BPP
    struct.pack_into("<i", header, 36, metrics["hSize"])
    struct.pack_into("<i", header, 40, metrics["vSize"])
    struct.pack_into("<i", header, 44, metrics["hResolution"])
    struct.pack_into("<i", header, 48, metrics["vResolution"])
    header[53:53 + len(metrics["fontName"])] = metrics["fontName"]
    header[117:117 + len(metrics["fontType"])] = metrics["fontType"]
    struct.pack_into("<H", header, 182, first)
    struct.pack_into("<H", header, 184, last)
    for i, key in enumerate(("maxAscender", "maxDescender", "maxLeftXAdjust",
                             "maxBaseYAdjust", "minCenterXAdjust", "maxTopYAdjust")):
        struct.pack_into("<i", header, 212 + i * 4, metrics[key])
    struct.pack_into("<ii", header, 236, metrics["maxAdvance"][0], metrics["maxAdvance"][1])
    struct.pack_into("<ii", header, 244, metrics["maxSize"][0], metrics["maxSize"][1])
    struct.pack_into("<HH", header, 252, metrics["maxGlyphWidth"], metrics["maxGlyphHeight"])
    header[258] = table_lengths[0]
    header[259] = table_lengths[1]
    header[260] = table_lengths[2]
    header[261] = table_lengths[3]
    struct.pack_into("<i", header, 364, 0)            # no shadow map
    struct.pack_into("<i", header, 368, 16)
    struct.pack_into("<i", header, 376, metrics["shadowScale"][0])
    struct.pack_into("<i", header, 380, metrics["shadowScale"][1])
    return header


def set_bits(buf: bytearray, count: int, position: int, value: int) -> None:
    for index in range(count):
        absolute = position + index
        byte = absolute // 8
        mask = 1 << (absolute & 7)
        if (value >> index) & 1:
            buf[byte] |= mask
        else:
            buf[byte] &= ~mask & 0xFF


class BitWriter:
    def __init__(self) -> None:
        self.data = bytearray()
        self.position = 0

    def put(self, count: int, value: int) -> None:
        need = (self.position + count + 7) // 8
        if len(self.data) < need:
            self.data.extend(b"\x00" * (need - len(self.data)))
        set_bits(self.data, count, self.position, value & ((1 << count) - 1))
        self.position += count


def encode_bitmap(rows: list[list[int]]) -> bytes:
    pixels = [value for row in rows for value in row]
    writer = BitWriter()
    index = 0
    while index < len(pixels):
        take = min(8, len(pixels) - index)
        writer.put(4, 16 - take)
        for offset in range(take):
            writer.put(4, pixels[index + offset])
        index += take
    return bytes(writer.data)


def rasterise(face: freetype.Face, char: str, pixel_size: int) -> dict | None:
    face.set_pixel_sizes(0, pixel_size)
    index = face.get_char_index(ord(char))
    if index == 0:
        return None
    face.load_glyph(index, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
    bitmap = face.glyph.bitmap
    width, height = bitmap.width, bitmap.rows
    if width == 0 or height == 0 or width > 127 or height > 127:
        return None
    buffer = bitmap.buffer
    pitch = bitmap.pitch
    rows = [[min(15, (buffer[y * pitch + x] + 8) // 17) for x in range(width)]
            for y in range(height)]
    left = face.glyph.bitmap_left
    top = face.glyph.bitmap_top
    if not (-64 <= left <= 63 and -64 <= top <= 63):
        return None
    return {"w": width, "h": height, "left": left, "top": top,
            "advance": face.glyph.advance.x, "rows": rows}


def metric_keys(glyph: dict) -> tuple[tuple[int, int], ...]:
    return (
        (glyph["w"] << 6, glyph["h"] << 6),
        (glyph["left"] << 6, glyph["left"] << 6),
        (glyph["top"] << 6, glyph["top"] << 6),
        (glyph["advance"], 0),
    )


def build_tables(glyphs: list[dict]) -> list[list[tuple[int, int]]]:
    tables: list[list[tuple[int, int]]] = []
    for slot in range(4):
        counts: dict[tuple[int, int], int] = {}
        for glyph in glyphs:
            entry = metric_keys(glyph)[slot]
            counts[entry] = counts.get(entry, 0) + 1
        ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        tables.append([entry for entry, _ in ordered[:MAX_TABLE_ENTRIES]])
    return tables


def metric_index(tables: list[list[tuple[int, int]]], glyph: dict, slot: int) -> int:
    table = tables[slot]
    entry = metric_keys(glyph)[slot]
    if entry in table:
        return table.index(entry)
    return min(range(len(table)),
               key=lambda i: abs(table[i][0] - entry[0]) + abs(table[i][1] - entry[1]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--chars", type=Path, required=True)
    parser.add_argument("--size", type=int, default=17)
    parser.add_argument("--metrics-from", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    template = args.metrics_from.read_bytes()
    metrics = {
        "hSize": struct.unpack_from("<i", template, 36)[0],
        "vSize": struct.unpack_from("<i", template, 40)[0],
        "hResolution": struct.unpack_from("<i", template, 44)[0],
        "vResolution": struct.unpack_from("<i", template, 48)[0],
        "fontName": b"GundamNEXTPlusKR",
        "fontType": b"Regular",
        "maxAscender": struct.unpack_from("<i", template, 212)[0],
        "maxDescender": struct.unpack_from("<i", template, 216)[0],
        "maxLeftXAdjust": struct.unpack_from("<i", template, 220)[0],
        "maxBaseYAdjust": struct.unpack_from("<i", template, 224)[0],
        "minCenterXAdjust": struct.unpack_from("<i", template, 228)[0],
        "maxTopYAdjust": struct.unpack_from("<i", template, 232)[0],
        "maxAdvance": list(struct.unpack_from("<ii", template, 236)),
        "maxSize": list(struct.unpack_from("<ii", template, 244)),
        "maxGlyphWidth": struct.unpack_from("<H", template, 252)[0],
        "maxGlyphHeight": struct.unpack_from("<H", template, 254)[0],
        "shadowScale": [struct.unpack_from("<i", template, 376)[0],
                        struct.unpack_from("<i", template, 380)[0]],
    }

    chars = args.chars.read_text(encoding="utf-8")
    wanted: dict[int, str] = {}
    for char in sorted(set(chars)):
        codepoint = ord(char)
        if codepoint < 0x80:
            wanted[codepoint] = char
        elif 0xAC00 <= codepoint <= 0xD7A3:
            wanted[HANGUL_BASE + (codepoint - 0xAC00)] = char
        elif codepoint == MARKER_CODEPOINT:
            wanted[MARKER_CODEPOINT] = char

    face = freetype.Face(str(args.font))
    rasterised: dict[int, dict] = {}
    for codepoint in sorted(wanted):
        glyph = rasterise(face, wanted[codepoint], args.size)
        if glyph is not None:
            rasterised[codepoint] = glyph

    glyph_list = list(rasterised.values())
    tables = build_tables(glyph_list)

    glyph_blob = bytearray()
    records: list[int] = []
    kept: list[int] = []
    for codepoint in sorted(rasterised):
        glyph = rasterised[codepoint]
        writer = BitWriter()
        writer.put(14, 0)                       # size patched below
        writer.put(7, glyph["w"])
        writer.put(7, glyph["h"])
        writer.put(7, glyph["left"] & 0x7F)
        writer.put(7, glyph["top"] & 0x7F)
        writer.put(6, FONT_PGF_BMP_H_ROWS | METRIC_INDEX_FLAGS)
        writer.put(2, 0); writer.put(2, 0); writer.put(3, 0)
        writer.put(9, 0)
        for slot in range(4):
            writer.put(8, metric_index(tables, glyph, slot))
        record = bytearray(writer.data)
        record.extend(encode_bitmap(glyph["rows"]))
        while len(record) % 4:
            record.append(0)
        set_bits(record, 14, 0, len(record))
        while len(glyph_blob) % 4:
            glyph_blob.append(0)
        records.append(len(glyph_blob) // 4)
        kept.append(codepoint)
        glyph_blob.extend(record)

    first = min(kept)
    last = max(kept)
    map_len = last - first + 1
    charmap = bytearray((map_len * MAP_BPE + 31) // 32 * 4)
    for index, codepoint in enumerate(kept):
        set_bits(charmap, MAP_BPE, (codepoint - first) * MAP_BPE, index)
    pointer = bytearray((len(records) * PTR_BPE + 31) // 32 * 4)
    for index, offset in enumerate(records):
        set_bits(pointer, PTR_BPE, index * PTR_BPE, offset)

    table_lengths = tuple(len(table) for table in tables)
    table_blob = bytearray()
    for table in tables:
        for first_value, second_value in table:
            table_blob += struct.pack("<II", first_value & 0xFFFFFFFF,
                                      second_value & 0xFFFFFFFF)

    header = build_header(metrics, map_len, len(records), first, last, table_lengths)
    out = (bytes(header) + bytes(table_blob) + bytes(charmap)
           + bytes(pointer) + bytes(glyph_blob))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(out)

    report = {
        "font": str(args.font),
        "output": str(args.output),
        "output_bytes": len(out),
        "glyphs": len(records),
        "skipped": len(wanted) - len(rasterised),
        "size": args.size,
        "table_lengths": list(table_lengths),
        "first_codepoint": f"{first:#06x}",
        "last_codepoint": f"{last:#06x}",
    }
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

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
import sys
from pathlib import Path

import freetype

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from make_hangul_poc import DISPLACED_HANGUL, RUNTIME_INDEX_GLYPHS  # noqa: E402

HEADER_SIZE = 392
MAP_BPE = 14
PTR_BPE = 19
BPP = 4

FONT_PGF_BMP_H_ROWS = 0x01
METRIC_INDEX_FLAGS = 0x04 | 0x08 | 0x10 | 0x20
HANGUL_BASE = 0x0100
MARKER_CODEPOINT = 0x25BC
MAX_TABLE_ENTRIES = 255

# Real fonts mark a character the font has no glyph for with all-ones in the
# character map (kr0.pgf fills 51518 of its 65487 slots with 0x3FFF).  Anything
# in range but below charPointerLength is a real glyph index, so leaving the
# unused slots at zero makes every missing character draw as glyph 0 -- which is
# whichever character happens to sort first, not a blank.
MISSING_GLYPH = (1 << MAP_BPE) - 1

# Constants every accepted PGF carries in these header slots.  The real
# sceFont_Library (Lib-PSP libfont) reads byte 32, byte 33 and byte 372 as
# alignment units for the character map, the glyph pointer table and the shadow
# map: it computes ``div $zero, size - 1, unit`` and traps with ``break 7`` when
# the unit is zero.  Leaving them zero kills the whole font, so copy the values
# kr0.pgf (a stock Sony font) and nanum_full.pgf (a ttf2pgf font) share.
HEADER_PAD1 = bytes((0x04, 0x04))
HEADER_PAD5 = bytes((0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00,
                     0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                     0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                     0x00, 0x00))
HEADER_PAD6 = bytes((0x04, 0x00))
HEADER_ALIGN_UNITS = bytes((0x04, 0x06, 0x00, 0x00))


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
    header[32:34] = HEADER_PAD1
    header[34] = BPP
    header[186:212] = HEADER_PAD5
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
    header[256:258] = HEADER_PAD6
    header[258] = table_lengths[0]
    header[259] = table_lengths[1]
    header[260] = table_lengths[2]
    header[261] = table_lengths[3]
    struct.pack_into("<i", header, 364, 0)            # no shadow map
    struct.pack_into("<i", header, 368, 16)
    header[372:376] = HEADER_ALIGN_UNITS
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
    """Nibble RLE: 1..7 run of that many plus one repeats of the next nibble,
    8..15 copy of 16 minus that many literal nibbles that follow.

    A nibble stream is byte-aligned, so this matches the writer's LSB-first
    packing without any extra work.  Runs matter: a glyph is mostly background.
    """
    pixels = [value for row in rows for value in row]
    writer = BitWriter()
    total = len(pixels)
    cursor = 0
    while cursor < total:
        run = 0
        while run < 8 and cursor + run < total and pixels[cursor + run] == pixels[cursor]:
            run += 1
        if run > 1:
            writer.put(4, run - 1)
            writer.put(4, pixels[cursor])
            cursor += run
            continue

        end = cursor
        while end < total - 1 and (end - cursor) < 8:
            if pixels[end] == pixels[end + 1]:
                break
            end += 1
        if end == total - 1 and (end - cursor) < 8:
            end += 1
        if end == cursor:
            end += 1
        writer.put(4, 16 - (end - cursor))
        while cursor < end:
            writer.put(4, pixels[cursor])
            cursor += 1
    return bytes(writer.data)


def rasterise(face: freetype.Face, char: str, pixel_size: int) -> dict | None:
    face.set_pixel_sizes(0, pixel_size)
    index = face.get_char_index(ord(char))
    if index == 0:
        return None
    face.load_glyph(index, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
    bitmap = face.glyph.bitmap
    width, height = bitmap.width, bitmap.rows
    advance = face.glyph.advance.x
    if width == 0 or height == 0:
        # Blank in this font at this size (space, and NanumGothic's backtick).
        # Keep the slot with a single transparent pixel so its advance still
        # applies and so glyph 0 stays blank.
        return {"w": 1, "h": 1, "left": 0, "top": 0,
                "advance": advance, "rows": [[0]]}
    if width > 127 or height > 127:
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
            "advance": advance, "rows": rows}


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
    parser.add_argument("--jp-font", type=Path,
                        help="font used for the original-text glyphs")
    parser.add_argument("--jp-index-map", type=Path,
                        help="index -> character JSON from collect_jp_index_map.py")
    parser.add_argument("--jp-limit", type=int, default=0,
                        help="keep only the N most used original-text glyphs (0 = all)")
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
    wanted: dict[int, tuple[str, int]] = {}
    for char in sorted(set(chars)):
        codepoint = ord(char)
        if codepoint < 0x80:
            code = codepoint
        elif 0xAC00 <= codepoint <= 0xD7A3:
            code = HANGUL_BASE + DISPLACED_HANGUL.get(codepoint, codepoint - 0xAC00)
        elif codepoint == MARKER_CODEPOINT:
            code = MARKER_CODEPOINT
        else:
            continue
        if code in wanted:
            raise SystemExit(f"{char!r} and {wanted[code][0]!r} both map to code {code:#06x}")
        wanted[code] = (char, 0)

    faces = [freetype.Face(str(args.font))]
    jp_codes: set[int] = set()
    if args.jp_index_map:
        if not args.jp_font:
            raise SystemExit("--jp-index-map needs --jp-font")
        faces.append(freetype.Face(str(args.jp_font)))
        table = json.loads(args.jp_index_map.read_text(encoding="utf-8"))["jp"]
        if args.jp_limit:
            table = dict(list(table.items())[: args.jp_limit])
        for index, char in table.items():
            code = HANGUL_BASE + int(index)
            if code not in wanted:
                wanted[code] = (char, 1)
                jp_codes.add(code)

    # The game fills these indices in at runtime, so they are not negotiable.
    runtime_codes: set[int] = set()
    for index, char in RUNTIME_INDEX_GLYPHS.items():
        code = HANGUL_BASE + index
        if code in wanted and wanted[code][1] == 0:
            raise SystemExit(f"runtime index {index} collides with {wanted[code][0]!r}")
        wanted[code] = (char, 0)
        jp_codes.discard(code)
        runtime_codes.add(code)

    rasterised: dict[int, dict] = {}
    for codepoint in sorted(wanted):
        char, slot = wanted[codepoint]
        glyph = rasterise(faces[slot], char, args.size)
        if glyph is not None:
            rasterised[codepoint] = glyph

    glyph_list = list(rasterised.values())
    tables = build_tables(glyph_list)

    # Header max values must agree with the glyphs we actually ship.
    metrics["maxAscender"] = max(g["top"] for g in glyph_list) << 6
    metrics["maxDescender"] = min(g["top"] - g["h"] for g in glyph_list) << 6
    metrics["maxLeftXAdjust"] = min(g["left"] for g in glyph_list) << 6
    metrics["maxBaseYAdjust"] = max(g["top"] for g in glyph_list) << 6
    metrics["minCenterXAdjust"] = min(g["left"] for g in glyph_list) << 6
    metrics["maxTopYAdjust"] = max(g["top"] for g in glyph_list) << 6
    metrics["maxAdvance"] = [max(g["advance"] for g in glyph_list), 0]
    metrics["maxSize"] = [max(g["w"] for g in glyph_list) << 6,
                          max(g["h"] for g in glyph_list) << 6]
    metrics["maxGlyphWidth"] = max(g["w"] for g in glyph_list)
    metrics["maxGlyphHeight"] = max(g["h"] for g in glyph_list)

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
    for slot in range(map_len):
        set_bits(charmap, MAP_BPE, slot * MAP_BPE, MISSING_GLYPH)
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
        "jp_glyphs": sum(1 for code in jp_codes if code in rasterised),
        "runtime_glyphs": sum(1 for code in runtime_codes if code in rasterised),
    }
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

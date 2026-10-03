"""Repair revision 021's font path collision with the game's ctype table.

The old zero-run placement overwrote live high-byte character classifications.
Keep the existing sceFontOpenUserFile import and place the path in the font
initializer's bypassed built-in font-selection setup, with an explicit branch
over the literal. No loaded segment is expanded and no zero-run is assumed free.
The original 257-byte table is verified against the ASCII classification rules:
https://github.com/pspdev/newlib/blob/master/newlib/libc/ctype/ctype_.c
https://github.com/pspdev/newlib/blob/master/newlib/libc/include/ctype.h
Runtime freeze causality and resolution require a separate user retest.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile

SOURCE_SHA256 = "ce917a0f7289ccce3a0db8f0783529f93ff31789c0ee0bb1842ce632f0dd0c06"
BASELINE_SHA256 = "29cba21ef1f6c9a8e198545dd927c3703841b1e7da08462ac6ab0ea414e64013"
CTYPE_VA = 0x08A01F7C
WINDOW_START = 0x089BC3D0
WINDOW_END = 0x089BC438
LITERAL_VA = 0x089BC3D8
OPEN_SETUP_VA = 0x089BC410
OPEN_STUB_VA = 0x08A00888
FONT_PATH = b"disc0:/PSP_GAME/SYSDIR/UPDATE/DATA.BIN\0"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def va_offset(data: bytes, va: int) -> int:
    elf = ELFFile(io.BytesIO(data))
    for section in elf.iter_sections():
        if section["sh_type"] == "SHT_NOBITS":
            continue
        if section["sh_addr"] <= va < section["sh_addr"] + section["sh_size"]:
            return section["sh_offset"] + va - section["sh_addr"]
    raise ValueError(f"No file-backed section for {va:#x}")


def ascii_ctype_table() -> bytes:
    table = bytearray([0])  # EOF entry, then unsigned byte values 0..255.
    for c in range(256):
        if c >= 128:
            flag = 0
        elif c < 32 or c == 127:
            flag = 32 | (8 if 9 <= c <= 13 else 0)
        elif c == 32:
            flag = 8 | 128
        elif 48 <= c <= 57:
            flag = 4
        elif 65 <= c <= 90:
            flag = 1 | (64 if c <= 70 else 0)
        elif 97 <= c <= 122:
            flag = 2 | (64 if c <= 102 else 0)
        else:
            flag = 16
        table.append(flag)
    return bytes(table)


def i_type(op: int, rs: int, rt: int, imm: int) -> int:
    return (op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def font_open_block(path: bytes = FONT_PATH) -> bytes:
    if not path.endswith(b"\0") or b"\0" in path[:-1]:
        raise ValueError("Font path must have exactly one trailing NUL")
    block = bytearray(WINDOW_END - WINDOW_START)
    branch = i_type(4, 0, 0, (OPEN_SETUP_VA - (WINDOW_START + 4)) // 4)
    struct.pack_into("<I", block, 0, branch)  # beq zero,zero; delay slot is nop.
    at = LITERAL_VA - WINDOW_START
    if at + len(path) > OPEN_SETUP_VA - WINDOW_START:
        raise ValueError("Literal overlaps executable open setup")
    block[at:at + len(path)] = path
    hi = (LITERAL_VA + 0x8000) >> 16
    words = [
        i_type(15, 0, 2, 0x08DC),            # lui v0, library handle global base
        i_type(35, 2, 4, 0x9D68),            # lw a0, -0x6298(v0)
        i_type(15, 0, 5, hi),                # lui a1, adjusted literal upper half
        i_type(9, 5, 5, LITERAL_VA),          # addiu a1,a1,literal lower half
        i_type(9, 0, 6, 1),                  # a2 = file-backed font mode
        i_type(9, 29, 7, 0xB8),              # a3 = existing stack error result
        (3 << 26) | ((OPEN_STUB_VA >> 2) & 0x03FFFFFF),
        0,                                  # jal delay slot
    ]
    struct.pack_into("<8I", block, OPEN_SETUP_VA - WINDOW_START, *words)
    return bytes(block)


def repair(source: bytes, baseline: bytes) -> tuple[bytes, dict]:
    if digest(source) != SOURCE_SHA256 or digest(baseline) != BASELINE_SHA256:
        raise ValueError("Original or revision 021 ELF hash does not match")
    table_off = va_offset(source, CTYPE_VA)
    original_table = source[table_off:table_off + 257]
    if original_table != ascii_ctype_table():
        raise ValueError("Source table differs from verified ASCII ctype layout")
    old_path_off = baseline.find(FONT_PATH)
    if old_path_off < table_off or old_path_off + len(FONT_PATH) > table_off + 257:
        raise ValueError("Baseline path is not wholly within the corrupted ctype table")
    if baseline.count(FONT_PATH) != 1:
        raise ValueError("Unexpected multiple baseline font paths")
    changed_indices = [i - 1 for i, (a, b) in enumerate(zip(original_table, baseline[table_off:table_off + 257])) if a != b]
    window_off = va_offset(source, WINDOW_START)
    window_size = WINDOW_END - WINDOW_START
    nid_off = 0x2010A4 + 22 * 4
    if struct.unpack_from("<I", baseline, nid_off)[0] != 0x57FCB733:
        raise ValueError("Expected sceFontOpenUserFile import is missing")
    block = font_open_block()
    result = bytearray(baseline)
    result[table_off:table_off + 257] = original_table
    result[window_off:window_off + window_size] = block
    allowed = [(table_off, table_off + 257), (window_off, window_off + window_size)]
    changes = [i for i, (a, b) in enumerate(zip(baseline, result)) if a != b]
    if len(result) != len(baseline) or any(not any(lo <= i < hi for lo, hi in allowed) for i in changes):
        raise AssertionError("Unexpected ELF size or write")
    if result[table_off:table_off + 257] != ascii_ctype_table():
        raise AssertionError("Repaired table does not match the original")
    return bytes(result), {
        "source_elf_sha256": digest(source), "baseline_elf_sha256": digest(baseline),
        "output_elf_sha256": digest(result), "elf_bytes": len(result),
        "ctype_table_va": f"0x{CTYPE_VA:08X}", "ctype_table_bytes": 257,
        "corrupted_unsigned_byte_indices": changed_indices,
        "old_font_path_offset": old_path_off, "new_font_path_va": f"0x{LITERAL_VA:08X}",
        "font_path_bytes": len(FONT_PATH), "modified_init_window": [f"0x{WINDOW_START:08X}", f"0x{WINDOW_END:08X}"],
        "allowed_file_ranges": allowed, "changed_elf_bytes": len(changes),
        "ctype_source_match": True, "other_elf_bytes_preserved": True,
        "elf_header_and_segment_geometry_preserved": True,
        "font_open_api_unchanged": True,
        "built_in_font_selection_bypassed": True,
        "runtime_verdict": "NOT_TESTED", "freeze_causality": "UNCONFIRMED",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_elf", type=Path)
    parser.add_argument("baseline_elf", type=Path)
    parser.add_argument("output_elf", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.output_elf.exists() or args.report.exists():
        parser.error("Use new output paths; existing artifacts are preserved")
    data, report = repair(args.original_elf.read_bytes(), args.baseline_elf.read_bytes())
    args.output_elf.parent.mkdir(parents=True, exist_ok=True)
    args.output_elf.write_bytes(data)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

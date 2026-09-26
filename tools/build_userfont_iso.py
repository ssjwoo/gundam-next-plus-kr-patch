#!/usr/bin/env python3
"""Assemble a development ISO that loads its own font from inside the disc.

Steps
  1. move the decoder's Hangul base from 0xAC00 to a compact block (default 0x0100)
     so the font's character map stays small,
  2. redirect the game's font open to sceFontOpenUserFile with a disc0 path,
  3. write the font into the ISO slot and rebuild the image.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from hanpatch.platforms.psp import iso9660

DECODER_VA = 0x089BC550
TEXT_OFF = 0x3C54
TEXT_VA = 0x08804000

NID_OFF = 0x2010A4
NID_INDEX = 22
NID_OLD = 0xEE232411          # sceFontSetAltCharacterCode, unused by our build
NID_NEW = 0x57FCB733          # sceFontOpenUserFile
STUB_USERFILE = 0x08A00888

DATA_OFF = 0x201AF8
DATA_VA = 0x08A01EA4
DATA_SIZE = 0xFCA0C

# The game opens this path at boot.  A release reads the font out of the disc;
# switch to ``ms0:/PSP/SAVEDATA/NPJH50107/kr.pgf`` to swap fonts on the
# emulator's memory stick without rebuilding the image.
DEFAULT_FONT_PATH = "disc0:/PSP_GAME/SYSDIR/UPDATE/DATA.BIN"


def i_type(op: int, rs: int, rt: int, imm: int) -> int:
    return (op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def j_type(op: int, target: int) -> int:
    return (op << 26) | ((target >> 2) & 0x03FFFFFF)


def word_offset(va: int) -> int:
    return TEXT_OFF + (va - TEXT_VA)


def find_free_run(blob: bytearray, offset: int, size: int, length: int) -> int:
    run = 0
    for index in range(size):
        if blob[offset + index] == 0:
            run += 1
            if run == length:
                return index + 1 - length
        else:
            run = 0
    raise SystemExit("no free run found")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-elf", type=Path, required=True)
    parser.add_argument("--font", type=Path)
    parser.add_argument("--embed-font-slot", default=None)
    parser.add_argument("--source-iso", type=Path, required=True)
    parser.add_argument("--output-elf", type=Path, required=True)
    parser.add_argument("--output-iso", type=Path, required=True)
    parser.add_argument("--hangul-base", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--font-path", default=DEFAULT_FONT_PATH)
    parser.add_argument("--keep-marker", action="store_true", default=True)
    args = parser.parse_args()

    patched = bytearray(args.source_elf.read_bytes())

    # 1. Decoder: Hangul base.
    decoder = list(struct.unpack_from("<18I", patched, word_offset(DECODER_VA)))
    if decoder[10] != i_type(0x0D, 0, 9, 0xAC00):
        raise SystemExit(f"unexpected decoder word 10: {decoder[10]:08x}")
    decoder[10] = i_type(0x0D, 0, 9, args.hangul_base)
    if args.keep_marker:
        if decoder[12] != i_type(0x0D, 0, 9, 0xACA5):
            raise SystemExit(f"unexpected decoder word 12: {decoder[12]:08x}")
        # the 0x81A5 pair now decodes to base + 0xA5
        decoder[12] = i_type(0x0D, 0, 9, (args.hangul_base + 0xA5) & 0xFFFF)
    struct.pack_into("<18I", patched, word_offset(DECODER_VA), *decoder)
    print(f"decoder Hangul base -> {args.hangul_base:#06x}")

    # 2. Font open redirect.
    struct.pack_into("<I", patched, NID_OFF + NID_INDEX * 4, NID_NEW)
    text = args.font_path.encode("ascii") + b"\x00"
    run_offset = find_free_run(patched, DATA_OFF, DATA_SIZE, 64)
    path_va = DATA_VA + run_offset
    patched[DATA_OFF + run_offset : DATA_OFF + run_offset + len(text)] = text

    expect = {
        0x089BC414: j_type(0x03, 0x08A00888),
        0x089BC424: 0x00003021,
        0x089BC42C: i_type(0x23, 2, 5, 0x9D64),
        0x089BC430: j_type(0x03, 0x08A00878),
    }
    write = {
        0x089BC414: 0x00000000,
        0x089BC424: i_type(0x09, 0, 6, 1),
        0x089BC428: i_type(0x0F, 0, 5, (path_va >> 16) & 0xFFFF),
        0x089BC42C: i_type(0x09, 5, 5, path_va & 0xFFFF),
        0x089BC430: j_type(0x03, STUB_USERFILE),
    }
    for va, expected in expect.items():
        actual = struct.unpack_from("<I", patched, word_offset(va))[0]
        if actual != expected:
            raise SystemExit(f"{va:#010x} is {actual:08x}, expected {expected:08x}")
    for va, value in write.items():
        struct.pack_into("<I", patched, word_offset(va), value)
    print(f"font path {args.font_path!r} at {path_va:#010x}")

    args.output_elf.parent.mkdir(parents=True, exist_ok=True)
    args.output_elf.write_bytes(bytes(patched))
    files = {"/PSP_GAME/SYSDIR/EBOOT.BIN": bytes(patched)}
    extra = ""
    if args.embed_font_slot:
        if not args.font:
            raise SystemExit("--embed-font-slot needs --font")
        font = args.font.read_bytes()
        files[args.embed_font_slot] = font
        extra = f" (font {len(font)} bytes in {args.embed_font_slot})"
    iso9660.write(args.source_iso, args.output_iso, files)
    print(f"wrote {args.output_elf.name} and {args.output_iso.name}{extra}")


if __name__ == "__main__":
    main()

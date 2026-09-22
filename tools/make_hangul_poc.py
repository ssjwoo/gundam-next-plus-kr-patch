#!/usr/bin/env python3
"""Build the first Korean-rendering proof for Gundam VS Gundam NEXT PLUS.

The patch switches sceFont from the Japanese to Korean firmware PGF and replaces
the title's Shift-JIS decoder wrapper with a compact two-byte Hangul decoder.
ASCII remains one byte.  Hangul syllables U+AC00..U+D7A3 are encoded as:

    lead  = 0x80 + ((codepoint - 0xAC00) >> 7)
    trail = 0x80 + ((codepoint - 0xAC00) & 0x7F)

This spans the precomposed Hangul block without NUL bytes.  The byte pair
0x81A5 is reserved for the game's CP932 down-triangle continuation marker
(U+25BC), so U+ACA5 is deliberately rejected by the encoder.  Keeping lead
bytes below 0xF0 is required because the game's outer text parser treats
0xF0-0xFF as one-byte control tokens before calling the decoder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from hanpatch.platforms.psp import iso9660


FONT_LANGUAGE_INSN_VA = 0x089BC3E0
DECODE_FUNCTION_VA = 0x089BC550
POC_STRING_FILE_OFFSET = 0x26E2C8
POC_SOURCE = "このゲームはオートセーブ機能に対応しています。"
POC_TARGET = "이 게임은 한글 출력을 지원합니다."
RESERVED_HANGUL_CODEPOINT = 0xACA5


def r_type(op: int, rs: int, rt: int, rd: int, shamt: int, funct: int) -> int:
    return (op << 26) | (rs << 21) | (rt << 16) | (rd << 11) | (shamt << 6) | funct


def i_type(op: int, rs: int, rt: int, imm: int) -> int:
    return (op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def decoder_words() -> list[int]:
    # Registers: a0=4, v0=2, t0=8, t1=9, zero=0, ra=31.
    return [
        i_type(0x23, 4, 8, 0),          # lw    t0, 0(a0)
        i_type(0x24, 8, 2, 0),          # lbu   v0, 0(t0)
        i_type(0x0B, 2, 9, 0x80),       # sltiu t1, v0, 0x80
        i_type(0x05, 9, 0, 12),         # bnez  t1, return
        i_type(0x09, 8, 8, 1),          # addiu t0, t0, 1 (delay slot)
        i_type(0x24, 8, 9, 0),          # lbu   t1, 0(t0)
        i_type(0x09, 2, 2, -0x80),      # addiu v0, v0, -0x80
        r_type(0, 0, 2, 2, 7, 0x00),    # sll   v0, v0, 7
        i_type(0x09, 9, 9, -0x80),      # addiu t1, t1, -0x80
        r_type(0, 2, 9, 2, 0, 0x21),    # addu  v0, v0, t1
        i_type(0x0D, 0, 9, 0xAC00),     # ori   t1, zero, 0xAC00
        r_type(0, 2, 9, 2, 0, 0x21),    # addu  v0, v0, t1
        i_type(0x0D, 0, 9, 0xACA5),     # ori   t1, zero, U+ACA5 (reserved pair 81 A5)
        i_type(0x05, 2, 9, 2),          # bne   v0, t1, return
        i_type(0x09, 8, 8, 1),          # addiu t0, t0, 1 (delay slot)
        i_type(0x0D, 0, 2, 0x25BC),     # ori   v0, zero, U+25BC (black down triangle)
        r_type(0, 31, 0, 0, 0, 0x08),   # return: jr ra
        i_type(0x2B, 4, 8, 0),          # sw    t0, 0(a0) (delay slot)
    ]


def encode_hangul(text: str) -> bytes:
    out = bytearray()
    for char in text:
        codepoint = ord(char)
        if codepoint < 0x80:
            out.append(codepoint)
        elif 0xAC00 <= codepoint <= 0xD7A3:
            if codepoint == RESERVED_HANGUL_CODEPOINT:
                raise ValueError("U+ACA5 is reserved for the CP932 0x81A5 continuation marker")
            index = codepoint - 0xAC00
            out.extend((0x80 + (index >> 7), 0x80 + (index & 0x7F)))
        else:
            raise ValueError(f"unsupported character U+{codepoint:04X}: {char!r}")
    return bytes(out)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def va_to_file_offset(path: Path, address: int) -> int:
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        for section in elf.iter_sections():
            start = section["sh_addr"]
            size = section["sh_size"]
            if start <= address < start + size:
                return section["sh_offset"] + address - start
    raise ValueError(f"address 0x{address:08X} is not in a file-backed section")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("elf", type=Path)
    parser.add_argument("output_elf", type=Path)
    parser.add_argument("--source-iso", type=Path)
    parser.add_argument("--output-iso", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if bool(args.source_iso) != bool(args.output_iso):
        raise SystemExit("--source-iso and --output-iso must be given together")

    original = args.elf.read_bytes()
    patched = bytearray(original)
    language_offset = va_to_file_offset(args.elf, FONT_LANGUAGE_INSN_VA)
    decoder_offset = va_to_file_offset(args.elf, DECODE_FUNCTION_VA)

    expected_language = struct.pack("<I", i_type(0x09, 0, 2, 1))
    if original[language_offset : language_offset + 4] != expected_language:
        raise SystemExit("font-language instruction precondition failed")
    patched[language_offset : language_offset + 4] = struct.pack(
        "<I", i_type(0x09, 0, 2, 3)
    )

    decoder_blob = b"".join(struct.pack("<I", word) for word in decoder_words())
    if len(decoder_blob) != 0x48:
        raise AssertionError("decoder must exactly replace the 0x48-byte function")
    patched[decoder_offset : decoder_offset + len(decoder_blob)] = decoder_blob

    source = POC_SOURCE.encode("cp932")
    found = bytes(original[POC_STRING_FILE_OFFSET : POC_STRING_FILE_OFFSET + len(source)])
    if found != source or original[POC_STRING_FILE_OFFSET + len(source)] != 0:
        raise SystemExit("PoC string precondition failed")
    target = encode_hangul(POC_TARGET)
    if len(target) > len(source):
        raise SystemExit("PoC target exceeds its fixed slot")
    patched[POC_STRING_FILE_OFFSET : POC_STRING_FILE_OFFSET + len(source)] = (
        target + b"\0" * (len(source) - len(target))
    )

    args.output_elf.parent.mkdir(parents=True, exist_ok=True)
    args.output_elf.write_bytes(patched)
    if args.source_iso:
        args.output_iso.parent.mkdir(parents=True, exist_ok=True)
        iso9660.write(
            args.source_iso,
            args.output_iso,
            {"/PSP_GAME/SYSDIR/EBOOT.BIN": bytes(patched)},
        )

    report = {
        "source_elf": str(args.elf.resolve()),
        "source_elf_sha256": sha256(original),
        "patched_elf": str(args.output_elf.resolve()),
        "patched_elf_sha256": sha256(patched),
        "patched_elf_size": len(patched),
        "font_language_patch": {
            "virtual_address": f"0x{FONT_LANGUAGE_INSN_VA:08X}",
            "file_offset": f"0x{language_offset:X}",
            "before": expected_language.hex(),
            "after": bytes(patched[language_offset : language_offset + 4]).hex(),
            "language": "Korean (3)",
        },
        "decoder_patch": {
            "virtual_address": f"0x{DECODE_FUNCTION_VA:08X}",
            "file_offset": f"0x{decoder_offset:X}",
            "size": len(decoder_blob),
            "sha256": sha256(decoder_blob),
            "mapping": "ASCII passthrough; custom Hangul pairs; 81 A5 -> U+25BC (U+ACA5 reserved)",
        },
        "poc_string": {
            "file_offset": f"0x{POC_STRING_FILE_OFFSET:X}",
            "source": POC_SOURCE,
            "target": POC_TARGET,
            "slot_bytes": len(source),
            "encoded_bytes": len(target),
            "encoded_hex": target.hex(" "),
        },
    }
    if args.output_iso:
        iso_bytes = args.output_iso.read_bytes()
        report["patched_iso"] = str(args.output_iso.resolve())
        report["patched_iso_size"] = len(iso_bytes)
        report["patched_iso_sha256"] = sha256(iso_bytes)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()

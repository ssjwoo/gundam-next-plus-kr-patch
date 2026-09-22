#!/usr/bin/env python3
"""Disassemble an address range from a PSP MIPS ELF .text section."""

from __future__ import annotations

import argparse
from pathlib import Path

from capstone import CS_ARCH_MIPS, CS_MODE_LITTLE_ENDIAN, CS_MODE_MIPS32, Cs
from elftools.elf.elffile import ELFFile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("elf", type=Path)
    parser.add_argument("start", type=lambda value: int(value, 0))
    parser.add_argument("end", type=lambda value: int(value, 0))
    args = parser.parse_args()

    with args.elf.open("rb") as stream:
        elf = ELFFile(stream)
        section = elf.get_section_by_name(".text")
        if section is None:
            raise SystemExit("ELF has no .text section")
        base = section["sh_addr"]
        code = section.data()

    first = args.start - base
    last = args.end - base
    if first < 0 or last > len(code) or first >= last:
        raise SystemExit("range is outside .text")
    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)
    for insn in md.disasm(code[first:last], args.start):
        print(f"0x{insn.address:08X}: {insn.mnemonic:<9} {insn.op_str}")


if __name__ == "__main__":
    main()

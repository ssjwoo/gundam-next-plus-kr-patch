#!/usr/bin/env python3
"""Show MIPS call sites and nearby instructions for PSP ELF targets."""

from __future__ import annotations

import argparse
from pathlib import Path
import struct

from capstone import CS_ARCH_MIPS, CS_MODE_LITTLE_ENDIAN, CS_MODE_MIPS32, Cs
from capstone.mips import MIPS_OP_IMM
from elftools.elf.elffile import ELFFile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("elf", type=Path)
    parser.add_argument("targets", nargs="+", type=lambda value: int(value, 0))
    parser.add_argument("--context", type=int, default=12)
    args = parser.parse_args()

    with args.elf.open("rb") as stream:
        elf = ELFFile(stream)
        section = elf.get_section_by_name(".text")
        if section is None:
            raise SystemExit("ELF has no .text section")
        code = section.data()
        address = section["sh_addr"]

    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)
    md.detail = True
    targets = set(args.targets)
    hits: list[tuple[int, int]] = []
    for offset in range(0, len(code) - 3, 4):
        word = struct.unpack_from("<I", code, offset)[0]
        if word >> 26 != 3:  # jal
            continue
        insn_address = address + offset
        target = ((insn_address + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
        if target in targets:
            hits.append((offset, target))

    for hit_no, (offset, target) in enumerate(hits, 1):
        hit_address = address + offset
        print(f"\n[{hit_no}] call 0x{target:08X} at 0x{hit_address:08X}")
        first = max(0, offset - args.context * 4)
        last = min(len(code), offset + (args.context + 2) * 4)
        for insn in md.disasm(code[first:last], address + first):
            marker = ">" if insn.address == hit_address else " "
            print(f"{marker} 0x{insn.address:08X}: {insn.mnemonic:<9} {insn.op_str}")

    print(f"\nhits={len(hits)}")


if __name__ == "__main__":
    main()

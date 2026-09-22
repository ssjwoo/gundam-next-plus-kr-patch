#!/usr/bin/env python3
"""Inventory printable CP932 C strings and direct pointers in a PSP ELF.

This is evidence collection, not a blind extractor: only non-executable
PROGBITS sections are scanned, every candidate must end in NUL, and every byte
must form a printable CP932 token.  Each exact string-start virtual address is
then searched as a 32-bit little-endian value to locate direct data pointers.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile


JP_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\u3005\u3006\u30fc]")
KANA_RE = re.compile(r"[\u3040-\u30ff\u3005\u3006\u30fc]")
LATIN_RE = re.compile(r"[A-Za-z]")
PRIVATE_RE = re.compile(r"[\ue000-\uf8ff]")
ALLOWED_CONTROLS = {"\n", "\r", "\t"}


def sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sections(path: Path) -> tuple[bytes, list[dict]]:
    blob = path.read_bytes()
    with io.BytesIO(blob) as stream:
        elf = ELFFile(stream)
        out = []
        for index, section in enumerate(elf.iter_sections()):
            header = section.header
            if header["sh_type"] != "SHT_PROGBITS":
                continue
            if int(header["sh_flags"]) & 0x4:  # SHF_EXECINSTR
                continue
            offset = int(header["sh_offset"])
            size = int(header["sh_size"])
            if not offset or not size or not int(header["sh_addr"]) or offset + size > len(blob):
                continue
            out.append(
                {
                    "index": index,
                    "name": section.name or f"section_{index}",
                    "offset": offset,
                    "end": offset + size,
                    "address": int(header["sh_addr"]),
                    "size": size,
                }
            )
    return blob, out


def token_length(blob: bytes, offset: int, end: int) -> int:
    value = blob[offset]
    if value in (0x09, 0x0A, 0x0D) or 0x20 <= value <= 0x7E:
        return 1
    if 0xA1 <= value <= 0xDF:
        return 1
    if (0x81 <= value <= 0x9F) or (0xE0 <= value <= 0xFC):
        if offset + 1 >= end:
            return 0
        trail = blob[offset + 1]
        if (0x40 <= trail <= 0x7E) or (0x80 <= trail <= 0xFC):
            return 2
    return 0


def printable(text: str) -> bool:
    return not PRIVATE_RE.search(text) and all(
        char.isprintable() or char in ALLOWED_CONTROLS for char in text
    )


def scan_strings(blob: bytes, section: dict, min_bytes: int) -> list[dict]:
    out = []
    i = section["offset"]
    end = section["end"]
    while i < end:
        first = token_length(blob, i, end)
        if not first:
            i += 1
            continue
        start = i
        i += first
        while i < end and blob[i] != 0:
            width = token_length(blob, i, end)
            if not width:
                break
            i += width
        if i >= end or blob[i] != 0:
            i = start + 1
            continue
        raw = blob[start:i]
        if len(raw) < min_bytes:
            i += 1
            continue
        try:
            text = raw.decode("cp932")
        except UnicodeDecodeError:
            i = start + 1
            continue
        if not printable(text):
            i = start + 1
            continue
        has_japanese = bool(JP_RE.search(text))
        has_latin = bool(LATIN_RE.search(text))
        if has_japanese:
            category = "japanese"
        elif has_latin:
            category = "latin"
        else:
            category = "symbols_or_numbers"
        out.append(
            {
                "id": "",
                "section": section["name"],
                "file_offset": start,
                "virtual_address": section["address"] + start - section["offset"],
                "byte_length": len(raw),
                "slot_end": i + 1,
                "category": category,
                "text": text,
                "raw_hex": raw.hex(" "),
                "pointer_refs": [],
            }
        )
        i += 1
    return out


def containing_section(offset: int, items: list[dict]) -> dict | None:
    for section in items:
        if section["offset"] <= offset < section["end"]:
            return section
    return None


def pointer_refs(blob: bytes, items: list[dict], strings: list[dict]) -> list[dict]:
    out = []
    searchable = [
        section for section in items if section["name"] == ".data" and section["size"] >= 4
    ]
    for item in strings:
        needle = struct.pack("<I", item["virtual_address"])
        for section in searchable:
            cursor = section["offset"]
            while True:
                hit = blob.find(needle, cursor, section["end"])
                if hit < 0:
                    break
                # Aligned 32-bit data fields are the pointer-table evidence.
                if (hit - section["offset"]) % 4 == 0:
                    ref = {
                        "file_offset": hit,
                        "virtual_address": section["address"] + hit - section["offset"],
                        "section": section["name"],
                        "target_id": item["id"],
                        "target_file_offset": item["file_offset"],
                        "target_virtual_address": item["virtual_address"],
                    }
                    out.append(ref)
                    item["pointer_refs"].append(hit)
                cursor = hit + 1
    return sorted(out, key=lambda value: (value["file_offset"], value["target_id"]))


def pointer_tables(refs: list[dict]) -> list[dict]:
    if not refs:
        return []
    groups: list[list[dict]] = []
    current = [refs[0]]
    for ref in refs[1:]:
        previous = current[-1]
        if (
            ref["section"] == previous["section"]
            and ref["file_offset"] == previous["file_offset"] + 4
        ):
            current.append(ref)
        else:
            groups.append(current)
            current = [ref]
    groups.append(current)
    out = []
    for index, group in enumerate(group for group in groups if len(group) >= 2):
        out.append(
            {
                "id": f"PT{index:04d}",
                "section": group[0]["section"],
                "file_offset_start": group[0]["file_offset"],
                "file_offset_end": group[-1]["file_offset"] + 4,
                "virtual_address_start": group[0]["virtual_address"],
                "entry_count": len(group),
                "targets": [ref["target_id"] for ref in group],
            }
        )
    return out


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("elf", type=Path)
    parser.add_argument("outdir", type=Path)
    parser.add_argument("--min-bytes", type=int, default=4)
    parser.add_argument("--fan-patch-csv", type=Path)
    args = parser.parse_args()

    blob, items = sections(args.elf)
    found = []
    for section in items:
        found.extend(scan_strings(blob, section, args.min_bytes))
    by_offset = {item["file_offset"]: item for item in found}
    fan_rows = []
    if args.fan_patch_csv:
        with args.fan_patch_csv.open(encoding="utf-8-sig", newline="") as stream:
            fan_rows = list(csv.DictReader(stream))
        for row in fan_rows:
            offset = int(row["offset"])
            item = by_offset.get(offset)
            if item is None:
                section = containing_section(offset, items)
                raw = bytes.fromhex(row["original_hex"])
                if section is None or blob[offset : offset + len(raw)] != raw:
                    raise SystemExit(
                        f"fan-patch evidence at 0x{offset:X} does not match the ELF"
                    )
                text = row["original"]
                if JP_RE.search(text):
                    category = "japanese"
                elif LATIN_RE.search(text):
                    category = "latin"
                else:
                    category = "symbols_or_numbers"
                item = {
                    "id": "",
                    "section": section["name"],
                    "file_offset": offset,
                    "virtual_address": section["address"] + offset - section["offset"],
                    "byte_length": len(raw),
                    "slot_end": offset + int(row["capacity_before_next_original_cell"]) + 1,
                    "category": category,
                    "text": text,
                    "raw_hex": raw.hex(" "),
                    "pointer_refs": [],
                }
                found.append(item)
                by_offset[offset] = item
            item["fan_patch_touched"] = True
            item["fan_patch_text"] = row["patched"]
            item["fan_patch_encoded_bytes"] = int(row["patched_bytes"])
            item["fan_patch_capacity"] = int(row["capacity_before_next_original_cell"])
    found.sort(key=lambda item: item["file_offset"])
    for index, item in enumerate(found):
        item["id"] = f"EBOOT_{index:05d}"
        item.setdefault("fan_patch_touched", False)
        item.setdefault("fan_patch_text", "")
        item.setdefault("fan_patch_encoded_bytes", 0)
        item.setdefault("fan_patch_capacity", item["byte_length"])

    refs = pointer_refs(blob, items, found)
    for item in found:
        has_kana = bool(KANA_RE.search(item["text"]))
        if item["fan_patch_touched"]:
            item["evidence"] = "fan_patch_modified"
        elif item["pointer_refs"]:
            item["evidence"] = "direct_32bit_pointer"
        elif has_kana:
            item["evidence"] = "nul_terminated_cp932_with_kana"
        else:
            item["evidence"] = "printable_cp932_candidate"
    tables = pointer_tables(refs)
    args.outdir.mkdir(parents=True, exist_ok=True)

    serial_strings = []
    for item in found:
        row = dict(item)
        row["file_offset_hex"] = f"0x{item['file_offset']:08X}"
        row["virtual_address_hex"] = f"0x{item['virtual_address']:08X}"
        row["pointer_ref_count"] = len(item["pointer_refs"])
        row["pointer_refs_hex"] = " ".join(
            f"0x{offset:08X}" for offset in item["pointer_refs"]
        )
        serial_strings.append(row)

    write_csv(
        args.outdir / "eboot_text_inventory.csv",
        serial_strings,
        [
            "id",
            "category",
            "section",
            "file_offset_hex",
            "virtual_address_hex",
            "byte_length",
            "pointer_ref_count",
            "pointer_refs_hex",
            "evidence",
            "fan_patch_touched",
            "fan_patch_text",
            "fan_patch_encoded_bytes",
            "fan_patch_capacity",
            "text",
            "raw_hex",
        ],
    )
    write_csv(
        args.outdir / "eboot_pointer_refs.csv",
        [
            {
                **ref,
                "file_offset_hex": f"0x{ref['file_offset']:08X}",
                "virtual_address_hex": f"0x{ref['virtual_address']:08X}",
                "target_file_offset_hex": f"0x{ref['target_file_offset']:08X}",
                "target_virtual_address_hex": f"0x{ref['target_virtual_address']:08X}",
            }
            for ref in refs
        ],
        [
            "file_offset_hex",
            "virtual_address_hex",
            "section",
            "target_id",
            "target_file_offset_hex",
            "target_virtual_address_hex",
        ],
    )
    (args.outdir / "eboot_text_inventory.json").write_text(
        json.dumps(serial_strings, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.outdir / "eboot_pointer_tables.json").write_text(
        json.dumps(tables, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    counts = {}
    for item in found:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    summary = {
        "source": str(args.elf.resolve()),
        "source_size": len(blob),
        "source_sha256": sha256(blob),
        "encoding": "CP932 (Windows Shift-JIS superset)",
        "scan_scope": "non-executable ELF SHT_PROGBITS sections",
        "sections": items,
        "string_count": len(found),
        "category_counts": counts,
        "fan_patch_confirmed_strings": sum(item["fan_patch_touched"] for item in found),
        "japanese_with_kana": sum(
            item["category"] == "japanese" and bool(KANA_RE.search(item["text"]))
            for item in found
        ),
        "strings_with_direct_pointer": sum(bool(item["pointer_refs"]) for item in found),
        "direct_pointer_count": len(refs),
        "contiguous_pointer_table_count": len(tables),
        "caveat": (
            "Direct 32-bit absolute pointers are proven. Strings with no direct hit may "
            "be reached by base-relative tables or constructed addresses and require "
            "code-level analysis before relocation."
        ),
    }
    (args.outdir / "eboot_inventory_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

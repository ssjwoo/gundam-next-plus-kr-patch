#!/usr/bin/env python3
"""Build and verify a fixed-slot Korean EBOOT from the translation workbook."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import struct

from hanpatch.platforms.psp import iso9660

from make_hangul_poc import (
    DECODE_FUNCTION_VA,
    FONT_LANGUAGE_INSN_VA,
    decoder_words,
    encode_hangul,
    i_type,
    va_to_file_offset,
)


EXPECTED_SOURCE_SHA256 = "ce917a0f7289ccce3a0db8f0783529f93ff31789c0ee0bb1842ce632f0dd0c06"
APPLY_STATUSES = {"translated", "approved"}
EXCLUDED_STATUSES = {"false_positive", "firmware_owned", "not_displayed"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_hangul(raw: bytes) -> str:
    out = []
    index = 0
    while index < len(raw):
        lead = raw[index]
        if lead < 0x80:
            out.append(chr(lead))
            index += 1
            continue
        if index + 1 >= len(raw):
            raise ValueError("truncated custom Hangul pair")
        trail = raw[index + 1]
        value = ((lead - 0x80) << 7) + (trail - 0x80) + 0xAC00
        if not 0xAC00 <= value <= 0xD7A3:
            raise ValueError(f"invalid custom Hangul pair {lead:02X} {trail:02X}")
        out.append(chr(value))
        index += 2
    return "".join(out)


def add_plan(plans: list[dict], owner: str, start: int, before: bytes, after: bytes) -> None:
    if len(before) != len(after):
        raise AssertionError("v1 write-plan entries must be fixed length")
    end = start + len(before)
    for existing in plans:
        if start < existing["end"] and existing["start"] < end:
            raise ValueError(f"write overlap: {owner} and {existing['owner']}")
    plans.append(
        {
            "owner": owner,
            "start": start,
            "end": end,
            "length": len(before),
            "before_sha256": sha256(before),
            "after_sha256": sha256(after),
            "before_hex": before.hex(" "),
            "after_hex": after.hex(" "),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_elf", type=Path)
    parser.add_argument("inventory_csv", type=Path)
    parser.add_argument("translations_csv", type=Path)
    parser.add_argument("output_elf", type=Path)
    parser.add_argument("--source-iso", type=Path)
    parser.add_argument("--output-iso", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--development-input-marker", type=Path)
    args = parser.parse_args()
    if bool(args.source_iso) != bool(args.output_iso):
        raise SystemExit("--source-iso and --output-iso must be supplied together")
    if args.allow_partial != bool(args.development_input_marker):
        raise SystemExit("partial builds require --allow-partial and --development-input-marker together")

    original = args.source_elf.read_bytes()
    if sha256(original) != EXPECTED_SOURCE_SHA256:
        raise SystemExit("source ELF hash does not match the analysed Japanese executable")
    development_input = None
    if args.development_input_marker:
        development_input = json.loads(args.development_input_marker.read_text(encoding="utf-8"))
        if (development_input.get("input_policy") != "development"
                or development_input.get("non_distributable") is not True
                or development_input.get("workbook_sha256") != sha256_file(args.translations_csv)
                or development_input.get("source_elf_sha256") != EXPECTED_SOURCE_SHA256):
            raise SystemExit("development input marker is missing, stale, or distributable")
    with args.inventory_csv.open(encoding="utf-8-sig", newline="") as handle:
        inventory = {row["id"]: row for row in csv.DictReader(handle)}
    with args.translations_csv.open(encoding="utf-8-sig", newline="") as handle:
        work = list(csv.DictReader(handle))
    ids = [row["id"] for row in work]
    if len(ids) != len(set(ids)):
        raise SystemExit("translation workbook contains duplicate ids")
    unknown = sorted(set(ids) - set(inventory))
    if unknown:
        raise SystemExit(f"translation workbook contains unknown ids: {unknown[:5]}")

    unresolved = [
        row["id"] for row in work
        if row["status"] not in APPLY_STATUSES | EXCLUDED_STATUSES
    ]
    not_approved = [row["id"] for row in work if row["status"] == "translated"]
    if not args.allow_partial and (unresolved or not_approved):
        raise SystemExit(
            f"release build refused: {len(unresolved)} unresolved and "
            f"{len(not_approved)} translated-but-unapproved rows"
        )

    patched = bytearray(original)
    plans: list[dict] = []
    language_offset = va_to_file_offset(args.source_elf, FONT_LANGUAGE_INSN_VA)
    language_before = struct.pack("<I", i_type(0x09, 0, 2, 1))
    language_after = struct.pack("<I", i_type(0x09, 0, 2, 3))
    if original[language_offset : language_offset + 4] != language_before:
        raise SystemExit("font-language instruction precondition failed")
    patched[language_offset : language_offset + 4] = language_after
    add_plan(plans, "font_language_ko", language_offset, language_before, language_after)

    decoder_offset = va_to_file_offset(args.source_elf, DECODE_FUNCTION_VA)
    decoder_after = b"".join(struct.pack("<I", word) for word in decoder_words())
    decoder_before = original[decoder_offset : decoder_offset + len(decoder_after)]
    patched[decoder_offset : decoder_offset + len(decoder_after)] = decoder_after
    add_plan(plans, "hangul_decoder", decoder_offset, decoder_before, decoder_after)

    applied = []
    pointer_checks = []
    for row in work:
        if row["status"] not in APPLY_STATUSES:
            continue
        target = row["target_ko"]
        if not target:
            raise SystemExit(f"{row['id']}: status {row['status']} has an empty target")
        source = inventory[row["id"]]
        offset = int(source["file_offset_hex"], 16)
        source_raw = bytes.fromhex(source["raw_hex"])
        if original[offset : offset + len(source_raw)] != source_raw:
            raise SystemExit(f"{row['id']}: source-byte precondition failed")
        if original[offset + len(source_raw)] != 0:
            raise SystemExit(f"{row['id']}: source terminator precondition failed")
        capacity = int(row["capacity_bytes"])
        if capacity < len(source_raw):
            raise SystemExit(f"{row['id']}: workbook capacity is smaller than source")
        encoded = encode_hangul(target)
        if len(encoded) > capacity:
            raise SystemExit(
                f"{row['id']}: {len(encoded)} encoded bytes exceed fixed capacity {capacity}"
            )
        span = capacity + 1
        before = original[offset : offset + span]
        after = encoded + bytes(span - len(encoded))
        patched[offset : offset + span] = after
        add_plan(plans, f"text/{row['id']}", offset, before, after)
        if decode_hangul(bytes(patched[offset : offset + len(encoded)])) != target:
            raise AssertionError(f"{row['id']}: immediate custom-codec readback failed")
        virtual_address = int(source["virtual_address_hex"], 16)
        for ref_text in source["pointer_refs_hex"].split():
            ref = int(ref_text, 16)
            expected = struct.pack("<I", virtual_address)
            if original[ref : ref + 4] != expected or patched[ref : ref + 4] != expected:
                raise AssertionError(f"{row['id']}: direct pointer changed at 0x{ref:X}")
            pointer_checks.append({"id": row["id"], "ref": ref_text, "target": source["virtual_address_hex"]})
        applied.append(
            {
                "id": row["id"],
                "offset": source["file_offset_hex"],
                "source": row["source_jp"],
                "target": target,
                "capacity": capacity,
                "encoded_bytes": len(encoded),
                "pointer_refs_verified": int(source["pointer_ref_count"]),
            }
        )

    owned = bytearray(len(original))
    for plan in plans:
        owned[plan["start"] : plan["end"]] = b"\x01" * plan["length"]
    unexpected = [
        index for index, (before, after) in enumerate(zip(original, patched))
        if before != after and not owned[index]
    ]
    if unexpected:
        raise AssertionError(f"{len(unexpected)} changed bytes are outside the write plan")

    output = bytes(patched)
    args.output_elf.parent.mkdir(parents=True, exist_ok=True)
    args.output_elf.write_bytes(output)
    if args.source_iso:
        args.output_iso.parent.mkdir(parents=True, exist_ok=True)
        iso9660.write(args.source_iso, args.output_iso, {"/PSP_GAME/SYSDIR/EBOOT.BIN": output})
        if args.output_iso.stat().st_size != args.source_iso.stat().st_size:
            raise AssertionError("ISO size changed")

    report = {
        "source_elf": str(args.source_elf.resolve()),
        "source_sha256": sha256(original),
        "output_elf": str(args.output_elf.resolve()),
        "output_sha256": sha256(output),
        "source_size": len(original),
        "output_size": len(output),
        "workbook_rows": len(work),
        "applied_rows": len(applied),
        "unresolved_rows": len(unresolved),
        "translated_unapproved_rows": len(not_approved),
        "excluded_rows": sum(row["status"] in EXCLUDED_STATUSES for row in work),
        "pointer_mode": "fixed slots; target addresses remain unchanged",
        "pointer_updates": 0,
        "direct_pointer_fields_readback_verified": len(pointer_checks),
        "write_plan_entries": len(plans),
        "unexpected_changed_bytes": 0,
        "partial_build": bool(unresolved or not_approved),
        "applied": applied,
        "write_plan": plans,
    }
    if args.output_iso:
        report.update(
            {
                "output_iso": str(args.output_iso.resolve()),
                "output_iso_size": args.output_iso.stat().st_size,
                "output_iso_sha256": sha256_file(args.output_iso),
            }
        )
    if development_input is not None:
        report["development_only"] = True
        report["distributable"] = False
        report["development_input_marker"] = str(args.development_input_marker.resolve())
    report_path = args.report or args.output_elf.with_suffix(args.output_elf.suffix + ".json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if development_input is not None:
        marker_path = (args.output_iso or args.output_elf).with_suffix(".development-only.json")
        marker = {
            "schema_version": 1,
            "non_distributable": True,
            "runtime_verified": False,
            "output_elf": str(args.output_elf.resolve()),
            "output_elf_sha256": report["output_sha256"],
            "output_iso": str(args.output_iso.resolve()) if args.output_iso else None,
            "output_iso_sha256": report.get("output_iso_sha256"),
            "workbook_sha256": development_input["workbook_sha256"],
            "unresolved_rows": len(unresolved),
            "translated_unapproved_rows": len(not_approved),
            "report": str(report_path.resolve()),
        }
        marker_path.write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in {"applied", "write_plan"}}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build an explicitly non-distribution catalog-revision development ISO.

All ELF writes come from a source-bound immutable plan. The exact baseline,
tokens, font codes, mission metadata, file geometry and final ISO bytes are
verified. No game or emulator is launched and existing outputs are refused.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import zlib

from elftools.elf.elffile import ELFFile
from hanpatch.platforms.psp import iso9660

from audit_workbook_font import font_records
from make_hangul_poc import decode_hangul, encode_hangul, RUNTIME_INDEX_GLYPHS
from validate_korean_catalog_revision import TOKEN

BASE_ISO_SHA256 = "886bd04022581981d0d391a7aa0e0044d8291e53cff112ac422d7fb8e88d2d8b"
BASE_ELF_SHA256 = "077e99a31d470b7b2234312197b0d3537b4e9a6e6af55efc497e9ebba3090781"
SOURCE_ELF_SHA256 = "ce917a0f7289ccce3a0db8f0783529f93ff31789c0ee0bb1842ce632f0dd0c06"
CHUNK = 8 * 1024 * 1024

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def file_sha(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as h:
        while data := h.read(CHUNK):
            result.update(data)
    return result.hexdigest()

def required_codes(text: str) -> set[int]:
    data, result, pos = encode_hangul(text), set(), 0
    while pos < len(data):
        lead = data[pos]
        if lead < 0x80:
            if lead >= 0x20:
                result.add(lead)
            pos += 1
        else:
            result.add(0x100 + (lead - 0x80) * 128 + data[pos + 1] - 0x80)
            pos += 2
    return result

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_iso", type=Path)
    parser.add_argument("baseline_elf", type=Path)
    parser.add_argument("original_elf", type=Path)
    parser.add_argument("plan_json", type=Path)
    parser.add_argument("font_pgf", type=Path)
    parser.add_argument("mission_records_jsonl", type=Path)
    parser.add_argument("recovered_csv", type=Path)
    parser.add_argument("output_iso", type=Path)
    args = parser.parse_args()
    manifest_path = args.output_iso.with_suffix(".manifest.json")
    output_elf = args.output_iso.with_suffix(".elf")
    output_csv = args.output_iso.with_suffix(".source_bound.csv")
    if any(p.exists() for p in (args.output_iso, manifest_path, output_elf, output_csv)):
        parser.error("Use a new candidate filename; outputs already exist")
    plan = json.loads(args.plan_json.read_bytes())
    if plan.get("errors") or plan.get("development_only") is not True:
        parser.error("Plan must be mechanically valid and explicitly development-only")
    baseline, source = args.baseline_elf.read_bytes(), args.original_elf.read_bytes()
    if sha(baseline) != BASE_ELF_SHA256 or sha(source) != SOURCE_ELF_SHA256:
        parser.error("ELF input revision mismatch")
    if plan["baseline_elf_sha256"] != sha(baseline) or plan["source_elf_sha256"] != sha(source):
        parser.error("Plan was prepared for a different source")
    patched = bytearray(baseline)
    data_section = ELFFile(io.BytesIO(baseline)).get_section_by_name(".data")
    start, end = data_section["sh_offset"], data_section["sh_offset"] + data_section["sh_size"]
    ranges, changed_by_id = [], {}
    font_records_by_code, font_info = font_records(args.font_pgf)
    for row in sorted(plan["changes"], key=lambda x:x["offset"]):
        off, span = row["offset"], row["capacity"] + 1
        raw = bytes.fromhex(row["source_raw_hex"])
        assert start <= off < off + span <= end
        assert source[off:off + len(raw)] == raw
        assert not any(source[off + len(raw):off + span])
        assert baseline[off:off + span] == bytes.fromhex(row["expected_before_hex"])
        assert not any(a < off + span and off < b for a,b in ranges), "Overlapping writers"
        assert not (off <= 0x28D3B4 < off + span), "Runtime digit table is protected"
        target = row["target_ko"]
        encoded = encode_hangul(target)
        assert len(encoded) <= row["capacity"]
        assert decode_hangul(encoded) == target
        assert TOKEN.findall(row["before_ko"]) == TOKEN.findall(target)
        assert required_codes(target) <= font_records_by_code.keys(), "Missing selected glyph"
        if row["slot_id"].startswith("NPMIS"):
            assert target.count("\n") == 3 and target.endswith("\n")
        patched[off:off + span] = encoded + bytes(span - len(encoded))
        ranges.append((off, off + span))
        changed_by_id[row["slot_id"]] = row
    assert len(patched) == len(baseline)
    for i,(a,b) in enumerate(zip(baseline, patched)):
        if a != b:
            assert any(lo <= i < hi for lo,hi in ranges), "Unexplained final ELF difference"
    code_before = ELFFile(io.BytesIO(baseline)).get_section_by_name(".text").data()
    assert ELFFile(io.BytesIO(patched)).get_section_by_name(".text").data() == code_before
    missions = [json.loads(line) for line in args.mission_records_jsonl.read_text(encoding="utf-8").splitlines()]
    translated_missions = 0
    for row in missions:
        off, capacity, ptr = int(row["file_offset_hex"],16), row["capacity_bytes"], int(row["pointer_ref_hex"],16)
        assert patched[off + capacity + 1:ptr + 4] == source[off + capacity + 1:ptr + 4]
        assert struct.unpack_from("<I", patched, ptr)[0] == 0x088003AC + off
        text = decode_hangul(bytes(patched[off:off+capacity+1]).split(b"\0",1)[0])
        if any(0xAC00 <= ord(c) <= 0xD7A3 for c in text):
            assert text.count("\n") == 3 and text.endswith("\n")
            translated_missions += 1
    with args.recovered_csv.open(encoding="utf-8-sig", newline="") as h:
        reader = csv.DictReader(h)
        fieldnames, workbook = reader.fieldnames, list(reader)
    workbook_ids = {row["id"] for row in workbook}
    for row in workbook:
        if row["id"] in changed_by_id:
            row["target_ko"] = changed_by_id[row["id"]]["target_ko"]
            row["note"] = json.dumps({"policy":"development_only", "review_state":"unapproved_draft",
                                      "integration_slot":row["id"]})
        off, span = int(row["file_offset_hex"],16), int(row["capacity_bytes"]) + 1
        encoded = encode_hangul(row["target_ko"])
        assert patched[off:off+span] == encoded + bytes(span - len(encoded))
    for slot_id, item in changed_by_id.items():
        if slot_id in workbook_ids:
            continue
        row = {key:"" for key in fieldnames}
        row.update({"id":slot_id,"group":"source_bound_revision","file_offset_hex":hex(item["offset"]),
                    "source_jp":item["source_jp"],"capacity_bytes":str(item["capacity"]),
                    "target_ko":item["target_ko"],"status":"translated",
                    "note":json.dumps({"policy":"development_only","review_state":"unapproved_draft"})})
        workbook.append(row)
    all_required = set().union(*(required_codes(row["target_ko"]) for row in workbook))
    all_required.update(0x100 + code for code in RUNTIME_INDEX_GLYPHS)
    assert all_required <= font_records_by_code.keys(), "Missing workbook/runtime glyph"
    if file_sha(args.baseline_iso) != BASE_ISO_SHA256:
        parser.error("ISO input differs from the accepted baseline")
    replacements = {"/PSP_GAME/SYSDIR/EBOOT.BIN":bytes(patched),
                    "/PSP_GAME/SYSDIR/UPDATE/DATA.BIN":args.font_pgf.read_bytes()}
    allowed, before_entries = [], {}
    with iso9660.Iso.from_path(args.baseline_iso) as iso:
        for entry in iso.walk():
            if not entry.is_dir:
                before_entries[entry.path] = (entry.lba, entry.size)
        for name, data in replacements.items():
            entry = iso.find(name)
            allocation = (entry.size + 2047) // 2048 * 2048
            assert len(data) <= allocation, "Would relocate ISO member; not allowed by this build"
            assert not any(iso.blob[entry.offset+entry.size:entry.offset+allocation]), "Unknown sector tail data"
            if name.endswith("EBOOT.BIN"):
                assert bytes(iso.blob[entry.offset:entry.offset+entry.size]) == baseline
            allowed.append((entry.offset, entry.offset + allocation))
            allowed.append((entry.record_offset + 10, entry.record_offset + 18))
    args.output_iso.parent.mkdir(parents=True, exist_ok=True)
    iso9660.write(args.baseline_iso, args.output_iso, replacements)
    assert args.output_iso.stat().st_size == args.baseline_iso.stat().st_size
    digest, crc, changed_disc = hashlib.sha256(), 0, 0
    with args.baseline_iso.open("rb") as left, args.output_iso.open("rb") as right:
        position = 0
        while before := left.read(CHUNK):
            after = right.read(len(before))
            digest.update(after); crc = zlib.crc32(after, crc)
            if before != after:
                for i,(a,b) in enumerate(zip(before,after)):
                    if a != b:
                        assert any(lo <= position+i < hi for lo,hi in allowed), "Unexpected ISO write"
                        changed_disc += 1
            position += len(before)
    with iso9660.Iso.from_path(args.output_iso) as iso:
        for entry in iso.walk():
            if entry.is_dir:
                continue
            old_lba, old_size = before_entries[entry.path]
            assert entry.lba == old_lba
            if entry.path not in replacements:
                assert entry.size == old_size
            else:
                expected = replacements[entry.path]
                assert entry.size == len(expected)
                assert bytes(iso.blob[entry.offset:entry.offset+entry.size]) == expected
    output_elf.write_bytes(patched)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as h:
        writer = csv.DictWriter(h,fieldnames=fieldnames); writer.writeheader();writer.writerows(workbook)
    manifest = {"development_only":True,"distribution_eligible":False,"baseline_iso_sha256":BASE_ISO_SHA256,
                "candidate_iso":str(args.output_iso.resolve()),"iso_sha256":digest.hexdigest(),
                "iso_crc32":f"{crc & 0xffffffff:08X}","iso_bytes":args.output_iso.stat().st_size,
                "elf_sha256":sha(bytes(patched)),"font":font_info,"changed_disc_bytes":changed_disc,
                "changed_text_slots":len(plan["changes"]),"mission_records":len(missions),
                "translated_complete_mission_records":translated_missions,"workbook_rows":len(workbook),
                "required_font_codes":len(all_required),"missing_font_codes":0,
                "plan_sha256":file_sha(args.plan_json),"source_bound_csv_sha256":file_sha(output_csv),
                "code_preserved":True,"digit_table_preserved":True,"mission_metadata_and_pointers_preserved":True,
                "unaffected_iso_bytes_preserved":True,"iso_member_lbas_preserved":True,
                "static_verdict":"PASS","runtime_verdict":"NOT_TESTED",
                "whole_game_text_complete":False,"graphics_localization_complete":False}
    manifest_path.write_bytes((json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode("utf-8"))
    print(json.dumps(manifest,ensure_ascii=True,indent=2))

if __name__ == "__main__":
    main()

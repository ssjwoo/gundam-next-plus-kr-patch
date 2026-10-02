#!/usr/bin/env python3
"""Recover existing Korean slot bytes against the verified Japanese/v19 ELFs.

This recovers a partial, unapproved workbook. It does not translate new strings,
infer source associations from old row IDs, or write a game artifact.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import struct
from collections import Counter, defaultdict
from pathlib import Path

from elftools.elf.elffile import ELFFile

from make_hangul_poc import decode_hangul, encode_hangul
from prepare_text_work import FIELDS
from parse_next_plus_mission_records import METADATA_BYTES, VIRTUAL_BASE


SOURCE_SHA256 = "ce917a0f7289ccce3a0db8f0783529f93ff31789c0ee0bb1842ce632f0dd0c06"
V19_SHA256 = "14f397f095d3acf34a498d2eb97f3ee74e24faac448a57717246475ff0f24756"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_slot(data: bytes) -> tuple[bytes, str]:
    if b"\0" not in data:
        raise ValueError("text extends beyond original candidate slot; capacity unresolved")
    raw = data.split(b"\0", 1)[0]
    text = decode_hangul(raw)
    if encode_hangul(text) != raw:
        raise ValueError("noncanonical codec output")
    if not text or any(data[len(raw):]):
        raise ValueError("changed slot is not NUL-padded within original budget")
    return raw, text


def merge_mission_inventory(inventory: list[dict], missions: list[dict],
                           original: bytes, v19: bytes, provided: bytes) -> tuple[list[dict], dict]:
    """Prefer verified complete mission records over scanner fragments."""
    mission_rows, spans, baseline_metadata_changes = [], [], []
    for record in missions:
        offset = int(record["file_offset_hex"], 16)
        capacity = record["capacity_bytes"]
        end = offset + capacity + 1
        pointer = int(record["pointer_ref_hex"], 16)
        raw = bytes.fromhex(record["source_raw_hex"])
        if not 0 <= offset < end <= pointer or pointer + 4 > len(original):
            raise ValueError("Mission bounds exceed the source ELF")
        if any(start < pointer + 4 and offset < stop for start, stop in spans):
            raise ValueError("Mission records overlap")
        metadata = original[end:pointer]
        if pointer - end != METADATA_BYTES or sha256(metadata) != record["metadata_sha256"]:
            raise ValueError("Mission metadata does not match original source")
        if struct.unpack_from("<I", original, pointer)[0] != VIRTUAL_BASE + offset:
            raise ValueError("Mission self-pointer is invalid")
        if provided[end:pointer + 4] != original[end:pointer + 4]:
            raise ValueError("Mission metadata or pointer changed in the supplied patch")
        baseline_metadata_verified = v19[end:pointer + 4] == original[end:pointer + 4]
        if not baseline_metadata_verified:
            baseline_metadata_changes.append(record["id"])
        if not record["source_jp"].endswith("\n") or record["source_jp"].count("\n") != 3:
            raise ValueError("Mission source does not contain the verified three-line structure")
        mission_rows.append({
            "id": record["id"], "stable_workbook_id": record["id"],
            "file_offset": offset, "virtual_address": VIRTUAL_BASE + offset,
            "raw_hex": raw.hex(), "text": record["source_jp"], "capacity_bytes": capacity,
            "category": "japanese_mission_record", "pointer_refs": [pointer],
            "evidence": "source_metadata_and_self_pointer_verified",
            "required_newlines": 3,
            "baseline_metadata_verified": baseline_metadata_verified,
        })
        spans.append((offset, pointer + 4))
    outside = [row for row in inventory if not any(start <= row["file_offset"] < end for start, end in spans)]
    return sorted(outside + mission_rows, key=lambda row: row["file_offset"]), {
        "structural_mission_records": len(mission_rows),
        "scanner_candidates_replaced_by_complete_mission_records": len(inventory) - len(outside),
        "v19_mission_metadata_changed_ids": baseline_metadata_changes,
        "provided_mission_metadata_and_pointers_match_original": True,
    }


def recover(original: bytes, v19: bytes, provided: bytes,
            inventory: list[dict], drafts: list[dict]) -> tuple[list[dict], list[dict], dict]:
    if sha256(original) != SOURCE_SHA256:
        raise ValueError("Japanese source ELF hash does not match the known source")
    if sha256(v19) != V19_SHA256:
        raise ValueError("v19 ELF hash does not match the public release")
    if len(provided) != len(original):
        raise ValueError("Provided ELF size differs; fixed source offsets are not verified")
    known_elf = ELFFile(io.BytesIO(v19))
    provided_elf = ELFFile(io.BytesIO(provided))
    def layout(elf: ELFFile) -> list[tuple]:
        return [(section.name, section["sh_type"], section["sh_offset"], section["sh_addr"],
                 section["sh_size"], section["sh_flags"]) for section in elf.iter_sections()]
    if layout(provided_elf) != layout(known_elf):
        raise ValueError("Provided ELF section layout differs; fixed source addresses are not verified")
    known_text = known_elf.get_section_by_name(".text")
    provided_text = provided_elf.get_section_by_name(".text")
    if known_text is None or provided_text is None or provided_text.data() != known_text.data():
        raise ValueError("Provided ELF code differs from v19; verify its codec before recovery")

    by_target: dict[str, list[str]] = defaultdict(list)
    for draft in drafts:
        by_target[draft["target_ko"]].append(draft["id"])
    restored, held = [], []
    seen_ids, seen_offsets = set(), set()
    for row in inventory:
        offset = row["file_offset"]
        source_raw = bytes.fromhex(row["raw_hex"])
        capacity = row.get("capacity_bytes", len(source_raw))
        end = offset + capacity + 1
        source_end = offset + len(source_raw) + 1
        if capacity < len(source_raw) or offset < 0 or end > len(original) or offset in seen_offsets:
            raise ValueError(f"Invalid or repeated inventory offset: {offset:#x}")
        seen_offsets.add(offset)
        if original[offset:source_end] != source_raw + b"\0" or any(original[source_end:end]):
            raise ValueError(f"Inventory source bytes differ at {offset:#x}")
        current, old = provided[offset:end], v19[offset:end]
        if current == original[offset:end] and old == original[offset:end]:
            continue
        if not any(char >= 0x80 for char in source_raw):
            continue
        try:
            if row["text"].encode("cp932") != source_raw:
                raise ValueError("CP932 alias cannot reproduce source bytes; preserve raw inventory")
            raw, text = canonical_slot(current)
            if "required_newlines" in row and text.count("\n") != row["required_newlines"]:
                raise ValueError("patched mission line structure differs from its source record")
            matches = by_target.get(text, [])
            if matches:
                provenance = "provided_patch_matches_public_korean_draft"
            elif row.get("evidence") == "source_metadata_and_self_pointer_verified" and current != original[offset:end]:
                # Complete mission records have independently verified boundaries
                # and an unchanged source self-pointer. Public scanner drafts can
                # contain only fragments of these three-line translations.
                provenance = "provided_patch_source_bound_structural_mission"
            else:
                if not row.get("baseline_metadata_verified", True):
                    raise ValueError("v19 mission metadata differs; public-target provenance required")
                _, old_text = canonical_slot(old)
                if old_text not in by_target or raw == source_raw:
                    raise ValueError("no public draft or v19 translation provenance for slot")
                provenance = "provided_patch_edit_of_verified_v19_translation"
            if not any(0xAC00 <= ord(char) <= 0xD7A3 for char in text):
                raise ValueError("no Korean syllable; requires semantic/manual review")
        except ValueError as exc:
            held.append({"source_id": row["id"], "offset": hex(offset),
                         "reason": str(exc), "source_jp": row["text"],
                         "provided_hex": current.hex()})
            continue
        restored.append({
            "id": row.get("stable_workbook_id", f"RESTORED_{offset:08X}"),
            "group": "recovered_mission_records" if "stable_workbook_id" in row else "recovered_source_slots",
            "file_offset_hex": hex(offset), "virtual_address_hex": hex(row["virtual_address"]),
            "source_category": row["category"], "source_jp": row["text"], "fan_english": "",
            "capacity_bytes": capacity, "hangul_budget_if_all_double_byte": capacity // 2,
            "pointer_ref_count": len(row["pointer_refs"]),
            "pointer_refs_hex": " ".join(hex(ptr) for ptr in row["pointer_refs"]),
            "evidence": row["evidence"], "target_ko": text, "status": "translated",
            "note": json.dumps({"recovered_from": "provided_patch", "provenance": provenance,
                                "review_state": "unapproved_draft", "original_extraction_id": row["id"],
                                "public_ids_with_same_target": matches}, ensure_ascii=False),
        })
        seen_ids.update(matches)
    report = {
        "source_elf_sha256": sha256(original), "v19_elf_sha256": sha256(v19),
        "provided_elf_sha256": sha256(provided), "provided_code_matches_v19": True,
        "restored_source_slots": len(restored), "held_changed_source_candidates": len(held),
        "public_draft_ids_with_matching_target_at_restored_slots": len(seen_ids),
        "public_draft_total": len(drafts), "hold_reasons": dict(Counter(row["reason"] for row in held)),
        "human_approved_rows": 0,
        "restored_mission_records": sum(row["group"] == "recovered_mission_records" for row in restored),
        "scope": "Partial byte-verified restoration; source-offset or verified mission IDs; no semantic, font, runtime or whole-workbook completion claim",
    }
    return restored, held, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_elf", type=Path)
    parser.add_argument("v19_elf", type=Path)
    parser.add_argument("provided_elf", type=Path)
    parser.add_argument("inventory_json", type=Path)
    parser.add_argument("draft_jsonl", type=Path)
    parser.add_argument("outdir", type=Path, help="New output directory; never overwrite a previous recovery")
    parser.add_argument("--mission-records", type=Path, help="Verified original structural_records.jsonl; replaces scanner fragments")
    args = parser.parse_args()
    if args.outdir.exists():
        parser.error(f"Output directory already exists: {args.outdir}")
    drafts = [json.loads(line) for line in args.draft_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    try:
        original, v19, provided = (path.read_bytes() for path in (args.source_elf, args.v19_elf, args.provided_elf))
        inventory = json.loads(args.inventory_json.read_text(encoding="utf-8"))
        mission_report = {}
        if args.mission_records:
            missions = [json.loads(line) for line in args.mission_records.read_text(encoding="utf-8").splitlines() if line.strip()]
            inventory, mission_report = merge_mission_inventory(inventory, missions, original, v19, provided)
        rows, held, report = recover(original, v19, provided, inventory, drafts)
        report.update(mission_report)
    except ValueError as exc:
        parser.error(str(exc))
    report["inputs"] = {key: str(getattr(args, key).resolve()) for key in (
        "source_elf", "v19_elf", "provided_elf", "inventory_json", "draft_jsonl")}
    report["inventory_sha256"] = sha256(args.inventory_json.read_bytes())
    report["draft_sha256"] = sha256(args.draft_jsonl.read_bytes())
    if args.mission_records:
        report["mission_records"] = str(args.mission_records.resolve())
        report["mission_records_sha256"] = sha256(args.mission_records.read_bytes())
    args.outdir.mkdir(parents=True, exist_ok=False)
    csv_path = args.outdir / "recovered_translations.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    report["workbook_sha256"] = sha256(csv_path.read_bytes())
    (args.outdir / "held_slots.json").write_text(json.dumps(held, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.outdir / "recovery_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

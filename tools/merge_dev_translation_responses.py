"""Merge validated external drafts into a non-distributable development workbook.

Protected fields come from the supported Japanese source workbook and EBOOT,
never from response files. Held or unencodable rows are left unchanged.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from make_hangul_poc import encode_hangul
from prepare_ai_translation_handoff import TOKEN_RE, sha256_file, source_fingerprint


ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "work" / "translation_handoff_v3"
BASE = ROOT / "work" / "text" / "translations_curated_nameflow.csv"
CURRENT = BASE
ORIGINAL = ROOT / "work" / "text" / "translations.csv"
INVENTORY = ROOT / "analysis" / "eboot_inventory" / "eboot_text_inventory.json"
SOURCE_ELF = ROOT / "analysis" / "original_decrypted_eboot.elf"
OUTPUT = ROOT / "work" / "text" / "translations_development_draft_2026-09-24.csv"
REPORT = ROOT / "analysis" / "development_draft_merge_2026-09-24.json"
MARKER = OUTPUT.with_suffix(".development-only.json")
EXPECTED_ELF_SHA256 = "ce917a0f7289ccce3a0db8f0783529f93ff31789c0ee0bb1842ce632f0dd0c06"
EDITABLE_FIELDS = {"target_ko", "status", "note"}


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def require_unique(rows: list[dict], label: str) -> dict[str, dict]:
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{label}: duplicate IDs")
    return {row["id"]: row for row in rows}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    manifest = json.loads((HANDOFF / "manifest.json").read_text(encoding="utf-8"))
    if sha256_file(BASE) != manifest["workbook_sha256"]:
        raise ValueError("base workbook does not match handoff manifest")
    if sha256_file(INVENTORY) != manifest["inventory_sha256"]:
        raise ValueError("source inventory does not match handoff manifest")
    if sha256_file(SOURCE_ELF) != EXPECTED_ELF_SHA256:
        raise ValueError("decrypted source EBOOT revision mismatch")

    fields, base_rows = read_csv(BASE)
    current_fields, current_rows = read_csv(CURRENT)
    original_fields, original_rows = read_csv(ORIGINAL)
    if fields != current_fields:
        raise ValueError("current workbook columns differ from source workbook")
    if fields != original_fields:
        raise ValueError("original workbook columns differ from handoff workbook")
    base_by_id = require_unique(base_rows, "base workbook")
    current_by_id = require_unique(current_rows, "current workbook")
    original_by_id = require_unique(original_rows, "original workbook")
    if list(base_by_id) != list(current_by_id):
        raise ValueError("current workbook IDs or ordering differ from source")
    if list(base_by_id) != list(original_by_id):
        raise ValueError("original workbook IDs or ordering differ from handoff")
    for row_id, current in current_by_id.items():
        base = base_by_id[row_id]
        if any(current[key] != base[key] for key in fields if key not in EDITABLE_FIELDS):
            raise ValueError(f"{row_id}: current workbook changed protected fields")
        if any(original_by_id[row_id][key] != base[key] for key in fields if key not in EDITABLE_FIELDS):
            raise ValueError(f"{row_id}: handoff workbook changed original protected fields")

    inventory_rows = json.loads(INVENTORY.read_text(encoding="utf-8"))
    inventory_by_id = require_unique(inventory_rows, "inventory")
    elf = SOURCE_ELF.read_bytes()
    planned: dict[str, tuple[str, str]] = {}
    skipped: list[dict] = []
    seen_external: set[str] = set()
    sources = [("evaluation", HANDOFF / "evaluation" / "evaluation.input.jsonl",
                HANDOFF / "evaluation" / "evaluation.response.jsonl",
                manifest["evaluation_input_sha256"])]
    for batch in manifest["batches"]:
        name = batch["name"]
        sources.append((name, HANDOFF / "production" / f"{name}.input.jsonl",
                        HANDOFF / "production" / f"{name}.response.jsonl",
                        batch["input_sha256"]))

    for name, input_path, response_path, expected_hash in sources:
        if sha256_file(input_path) != expected_hash:
            raise ValueError(f"{name}: input hash differs from manifest")
        inputs = read_jsonl(input_path)
        responses = read_jsonl(response_path)
        if [row["id"] for row in inputs] != [row["id"] for row in responses]:
            raise ValueError(f"{name}: response IDs or ordering differ from input")
        for source, response in zip(inputs, responses):
            row_id = source["id"]
            if row_id in seen_external:
                raise ValueError(f"{row_id}: duplicated across handoff batches")
            seen_external.add(row_id)
            if row_id not in base_by_id or row_id not in inventory_by_id:
                raise ValueError(f"{row_id}: no supported source record")
            workbook = base_by_id[row_id]
            inv = inventory_by_id[row_id]
            if source_fingerprint(source) != source["baseline"]:
                raise ValueError(f"{row_id}: source fingerprint mismatch")
            if response["baseline"] != source["baseline"]:
                raise ValueError(f"{row_id}: response baseline mismatch")
            if source["source_jp"] != workbook["source_jp"]:
                raise ValueError(f"{row_id}: Japanese source changed")
            if int(source["capacity_bytes"]) != int(workbook["capacity_bytes"]):
                raise ValueError(f"{row_id}: slot capacity changed")
            if bytes.fromhex(source["source_raw_hex"]) != bytes.fromhex(inv["raw_hex"]):
                raise ValueError(f"{row_id}: source raw bytes changed")
            if source["protected_tokens"] != TOKEN_RE.findall(workbook["source_jp"]):
                raise ValueError(f"{row_id}: source token inventory changed")
            offset = int(workbook["file_offset_hex"], 16)
            raw = bytes.fromhex(inv["raw_hex"])
            if elf[offset:offset + len(raw) + 1] != raw + b"\0":
                raise ValueError(f"{row_id}: supported ELF bytes or terminator changed")
            if current_by_id[row_id]["target_ko"]:
                raise ValueError(f"{row_id}: external draft overlaps an existing translation")

            status = response["status"]
            target = response["target_ko"]
            if status != "draft":
                skipped.append({"id": row_id, "source": name, "reason": status})
                continue
            if not isinstance(target, str) or not target.strip():
                raise ValueError(f"{row_id}: empty draft")
            if TOKEN_RE.findall(target) != source["protected_tokens"]:
                raise ValueError(f"{row_id}: protected token order changed")
            if any(ord(char) < 0x20 for char in target):
                raise ValueError(f"{row_id}: raw control character in draft")
            try:
                encoded = encode_hangul(target)
            except ValueError as exc:
                skipped.append({"id": row_id, "source": name, "reason": "encoding", "detail": str(exc)})
                continue
            capacity = int(workbook["capacity_bytes"])
            if len(encoded) > capacity:
                skipped.append({"id": row_id, "source": name, "reason": "slot_overflow",
                                "encoded_bytes": len(encoded), "capacity_bytes": capacity})
                continue
            planned[row_id] = (target, name)

    expected_external = manifest["counts"]["evaluation"] + manifest["counts"]["production"]
    if len(seen_external) != expected_external:
        raise ValueError(f"handoff population changed: {len(seen_external)} != {expected_external}")

    merged = []
    for row in current_rows:
        new_row = dict(row)
        if row["id"] in planned:
            target, source_name = planned[row["id"]]
            new_row["target_ko"] = target
            new_row["status"] = "translated"
            new_row["note"] = f"DEVELOPMENT_ONLY: external draft {source_name}; human approval pending"
        merged.append(new_row)
    applied = sum(row["status"] == "translated" for row in merged)
    if applied != 120 + len(planned):
        raise ValueError("unexpected translated row total")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(merged)
    temporary.replace(OUTPUT)

    marker = {
        "schema_version": 1,
        "input_policy": "development",
        "non_distributable": True,
        "workbook_sha256": sha256_file(OUTPUT),
        "source_elf_sha256": EXPECTED_ELF_SHA256,
        "handoff_manifest_sha256": sha256_file(HANDOFF / "manifest.json"),
        "selected_external_drafts": len(planned),
        "existing_unapproved_translations": 120,
    }
    MARKER.write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "schema_version": 1,
        "output_workbook": str(OUTPUT),
        "output_workbook_sha256": marker["workbook_sha256"],
        "development_marker": str(MARKER),
        "external_rows": len(seen_external),
        "selected_external_drafts": len(planned),
        "existing_unapproved_translations": 120,
        "total_translated_unapproved": applied,
        "remaining_workbook_rows": len(merged) - applied,
        "skipped_by_reason": dict(Counter(item["reason"] for item in skipped)),
        "selected_ids": sorted(planned),
        "skipped": skipped,
        "non_distributable": True,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in {"selected_ids", "skipped"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

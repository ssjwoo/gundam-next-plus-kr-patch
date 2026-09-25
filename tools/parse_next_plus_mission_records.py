"""Parse NEXT-PLUS mission records from the original EBOOT's pointer chain.

The older text scanner misses strings containing a fullwidth space. This
parser starts at the first verified mission record and follows the repeated
text -> alignment -> 44-byte metadata -> self-pointer structure. It never
modifies the game image or treats a failed link as a valid end without review.
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "analysis/original_decrypted_eboot.elf"
OUTPUT = ROOT / "work/next_plus_mission_handoff_v2"
SOURCE_SHA256 = "ce917a0f7289ccce3a0db8f0783529f93ff31789c0ee0bb1842ce632f0dd0c06"
FIRST_TEXT_OFFSET = 0x28ED18
VIRTUAL_BASE = 0x088003AC
METADATA_BYTES = 0x2C
MAX_RECORDS = 500
VARIABLE_RE = re.compile(r"%(?:\d+\$)?[-+ #0]*(?:\d+|\*)?(?:\.\d+)?[diuoxXfFeEgGcsp%]")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                    for row in rows), encoding="utf-8")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    source = SOURCE.read_bytes()
    if sha256_bytes(source) != SOURCE_SHA256:
        raise ValueError("source EBOOT revision mismatch")
    old_inventory = json.loads((ROOT / "analysis/eboot_inventory/eboot_text_inventory.json").read_text(encoding="utf-8"))
    old_by_offset = {row["file_offset"]: row for row in old_inventory}
    records: list[dict] = []
    unresolved: list[dict] = []
    cursor = FIRST_TEXT_OFFSET
    stop: dict | None = None
    for ordinal in range(1, MAX_RECORDS + 1):
        if cursor + 8 >= len(source):
            stop = {"reason": "end_of_elf", "offset_hex": f"0x{cursor:08X}"}
            break
        terminator = source.find(b"\0", cursor, min(len(source), cursor + 512))
        if terminator < 0:
            stop = {"reason": "no_terminator_within_512", "offset_hex": f"0x{cursor:08X}"}
            break
        aligned = (terminator + 4) & ~3
        pointer_at = aligned + METADATA_BYTES
        if pointer_at + 4 > len(source):
            stop = {"reason": "metadata_out_of_bounds", "offset_hex": f"0x{cursor:08X}"}
            break
        actual_pointer = struct.unpack_from("<I", source, pointer_at)[0]
        expected_pointer = VIRTUAL_BASE + cursor
        if actual_pointer != expected_pointer:
            stop = {"reason": "pointer_chain_end_or_different_structure",
                    "offset_hex": f"0x{cursor:08X}",
                    "pointer_at_hex": f"0x{pointer_at:08X}",
                    "actual_pointer_hex": f"0x{actual_pointer:08X}",
                    "expected_pointer_hex": f"0x{expected_pointer:08X}"}
            break
        raw = source[cursor:terminator]
        try:
            decoded = raw.decode("cp932")
        except UnicodeDecodeError as exc:
            decoded = None
            issue = f"cp932_decode_error: {exc}"
        else:
            bad_controls = [f"U+{ord(char):04X}" for char in decoded
                            if ord(char) < 0x20 and char != "\n"]
            if bad_controls:
                issue = "unexpected_controls: " + ",".join(sorted(set(bad_controls)))
            elif not decoded.endswith("\n") or decoded.count("\n") != 3:
                issue = f"unexpected_line_shape: {decoded.count(chr(10))} newlines"
            else:
                issue = None
        id_ = f"NPMIS_{ordinal:04d}"
        legacy = old_by_offset.get(cursor)
        entry = {
            "id": id_,
            "record_index": ordinal,
            "source_jp": decoded,
            "source_lines": decoded[:-1].split("\n") if decoded is not None and decoded.endswith("\n") else None,
            "source_raw_hex": raw.hex(" "),
            "source_byte_count": len(raw),
            "capacity_bytes": aligned - cursor - 1,
            "file_offset_hex": f"0x{cursor:08X}",
            "virtual_address_hex": f"0x{expected_pointer:08X}",
            "pointer_ref_hex": f"0x{pointer_at:08X}",
            "metadata_sha256": sha256_bytes(source[aligned:pointer_at]),
            "metadata_bytes": METADATA_BYTES,
            "newline_count": decoded.count("\n") if decoded is not None else None,
            "protected_tokens": VARIABLE_RE.findall(decoded) if decoded is not None else None,
            "legacy_eboot_id": legacy["id"] if legacy else None,
            "fan_english_reference": legacy["fan_patch_text"] if legacy and legacy["fan_patch_touched"] else "",
        }
        baseline_keys = ("id", "source_raw_hex", "file_offset_hex", "pointer_ref_hex",
                         "capacity_bytes", "metadata_sha256")
        canonical = json.dumps({key: entry[key] for key in baseline_keys},
                               sort_keys=True, separators=(",", ":")).encode("utf-8")
        entry["baseline"] = "sha256:" + sha256_bytes(canonical)
        if issue:
            unresolved.append({"id": id_, "reason": issue, "file_offset_hex": entry["file_offset_hex"]})
        records.append(entry)
        cursor = pointer_at + 4
    else:
        stop = {"reason": "max_record_guard", "offset_hex": f"0x{cursor:08X}"}

    if not records:
        raise ValueError("no structurally verified records")
    ids = [row["id"] for row in records]
    if len(ids) != len(set(ids)):
        raise AssertionError("duplicate structural IDs")
    ready = [row for row in records if row["source_jp"] is not None
             and row["source_jp"].endswith("\n") and row["newline_count"] == 3
             and row["id"] not in {item["id"] for item in unresolved}]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUTPUT / "mission.input.jsonl", ready)
    write_jsonl(OUTPUT / "mission.response.jsonl", [
        {"id": row["id"], "baseline": row["baseline"], "target_ko": "",
         "status": "pending", "notes": "", "questions": []} for row in ready
    ])
    write_jsonl(OUTPUT / "structural_records.jsonl", records)
    write_jsonl(OUTPUT / "unresolved_structure.jsonl", unresolved)
    report = {
        "schema_version": 2,
        "source_elf_sha256": SOURCE_SHA256,
        "first_text_offset_hex": f"0x{FIRST_TEXT_OFFSET:08X}",
        "virtual_base_hex": f"0x{VIRTUAL_BASE:08X}",
        "metadata_bytes_per_record": METADATA_BYTES,
        "structurally_verified_records": len(records),
        "translation_ready_records": len(ready),
        "unresolved_records": len(unresolved),
        "legacy_inventory_matches": sum(bool(row["legacy_eboot_id"]) for row in records),
        "newly_recovered_records": sum(not row["legacy_eboot_id"] for row in records),
        "newline_histogram": dict(sorted(Counter(row["newline_count"] for row in records).items())),
        "stop": stop,
        "input_sha256": sha256_bytes((OUTPUT / "mission.input.jsonl").read_bytes()),
        "response_template_sha256": sha256_bytes((OUTPUT / "mission.response.jsonl").read_bytes()),
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Create the auditable Korean translation workbook from the EBOOT inventory."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FIELDS = [
    "id", "group", "file_offset_hex", "virtual_address_hex", "source_category", "source_jp",
    "fan_english", "capacity_bytes", "hangul_budget_if_all_double_byte",
    "pointer_ref_count", "pointer_refs_hex", "evidence", "target_ko", "status", "note",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory_csv", type=Path)
    parser.add_argument("outdir", type=Path)
    args = parser.parse_args()
    with args.inventory_csv.open(encoding="utf-8-sig", newline="") as handle:
        source = list(csv.DictReader(handle))
    selected = [
        row
        for row in source
        if any(value >= 0x80 for value in bytes.fromhex(row["raw_hex"]))
        or row["fan_patch_touched"] == "True"
    ]
    selected.sort(key=lambda row: int(row["file_offset_hex"], 16))
    rows = []
    group_index = -1
    previous_end = -1
    for row in selected:
        offset = int(row["file_offset_hex"], 16)
        capacity = int(row["fan_patch_capacity"] if row["fan_patch_touched"] == "True" else row["byte_length"])
        if previous_end < 0 or offset - previous_end > 0x80:
            group_index += 1
        previous_end = offset + capacity + 1
        rows.append(
            {
                "id": row["id"],
                "group": f"data_run_{group_index:04d}",
                "file_offset_hex": row["file_offset_hex"],
                "virtual_address_hex": row["virtual_address_hex"],
                "source_category": row["category"],
                "source_jp": row["text"],
                "fan_english": row["fan_patch_text"],
                "capacity_bytes": capacity,
                "hangul_budget_if_all_double_byte": capacity // 2,
                "pointer_ref_count": row["pointer_ref_count"],
                "pointer_refs_hex": row["pointer_refs_hex"],
                "evidence": row["evidence"],
                "target_ko": "",
                "status": "todo",
                "note": "",
            }
        )
    args.outdir.mkdir(parents=True, exist_ok=True)
    csv_path = args.outdir / "translations.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "source_inventory": str(args.inventory_csv.resolve()),
        "rows": len(rows),
        "non_ascii_source_rows": sum(
            any(value >= 0x80 for value in bytes.fromhex(row["raw_hex"])) for row in selected
        ),
        "fan_patch_confirmed": sum(row["evidence"] == "fan_patch_modified" for row in rows),
        "direct_pointer_evidence": sum(row["evidence"] == "direct_32bit_pointer" for row in rows),
        "kana_candidate_evidence": sum(row["evidence"] == "nul_terminated_cp932_with_kana" for row in rows),
        "printable_candidate_evidence": sum(row["evidence"] == "printable_cp932_candidate" for row in rows),
        "groups": group_index + 1,
        "status": {"todo": len(rows), "translated": 0, "approved": 0},
        "warning": "Rows are candidates until context review; status=approved is required for a release build.",
    }
    (args.outdir / "translations_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

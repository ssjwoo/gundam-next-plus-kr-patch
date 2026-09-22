#!/usr/bin/env python3
"""Apply a reviewed translation batch to the workbook with hard preconditions."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re

from make_hangul_poc import encode_hangul


TAG_RE = re.compile(r"~[A-Za-z][A-Za-z0-9]?")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("batch", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.workbook.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    batch = json.loads(args.batch.read_text(encoding="utf-8"))
    if not isinstance(batch, list):
        raise SystemExit("batch must be a JSON list")
    by_id = {row["id"]: row for row in rows}
    seen = set()
    applied = []
    for entry in batch:
        row_id = entry["id"]
        if row_id in seen:
            raise SystemExit(f"duplicate batch id {row_id}")
        seen.add(row_id)
        if row_id not in by_id:
            raise SystemExit(f"unknown workbook id {row_id}")
        row = by_id[row_id]
        if row["source_jp"] != entry["source"]:
            raise SystemExit(f"{row_id}: source precondition failed")
        target = entry["target"]
        if TAG_RE.findall(row["source_jp"]) != TAG_RE.findall(target):
            raise SystemExit(f"{row_id}: ordered control-tag skeleton changed")
        encoded = encode_hangul(target)
        capacity = int(row["capacity_bytes"])
        if len(encoded) > capacity:
            raise SystemExit(f"{row_id}: {len(encoded)} bytes exceed {capacity}-byte slot")
        row["target_ko"] = target
        row["status"] = "translated"
        row["note"] = entry.get("note", "curated Korean draft; independent QA pending")
        applied.append(
            {"id": row_id, "encoded_bytes": len(encoded), "capacity_bytes": capacity, "slack": capacity - len(encoded)}
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(args.output)
    report = {
        "workbook": str(args.workbook.resolve()),
        "batch": str(args.batch.resolve()),
        "output": str(args.output.resolve()),
        "applied": len(applied),
        "minimum_slack_bytes": min((row["slack"] for row in applied), default=0),
        "rows": applied,
    }
    report_path = args.output.with_suffix(".curated.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

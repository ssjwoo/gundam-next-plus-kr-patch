#!/usr/bin/env python3
"""Merge reviewed machine-translation responses back into the workbook.

Only ``draft`` responses are applied.  ``needs_context``, ``not_text_candidate``
and ``needs_term_decision`` are held: the row keeps whatever it had and the
reason is recorded in the report.

Every applied row is re-checked against the same rules the build enforces:
protected tokens survive in order, the text stays inside the fixed byte slot,
and the custom codec accepts every character.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_hangul_poc import encode_hangul  # noqa: E402

TOKEN_RE = re.compile(r"~[A-Za-z0-9][A-Za-z0-9]?|%[A-Za-z]")
APPLY_STATUS = "draft"


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--note", default="MT review 2026-09-26; human approval pending")
    args = parser.parse_args()

    with args.workbook.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    by_id = {row["id"]: row for row in rows}

    inputs = read_jsonl(args.input)
    responses = read_jsonl(args.response)
    if [item["id"] for item in inputs] != [item["id"] for item in responses]:
        raise SystemExit("response ids or ordering differ from the handoff input")

    counts: Counter[str] = Counter()
    held: list[dict] = []
    problems: list[dict] = []
    applied: list[dict] = []

    for source, response in zip(inputs, responses):
        row_id = source["id"]
        row = by_id.get(row_id)
        if row is None:
            raise SystemExit(f"{row_id}: not in the workbook")
        if response["baseline"] != source["baseline"]:
            raise SystemExit(f"{row_id}: response baseline mismatch")
        status = response["status"]
        counts[status] += 1
        if status != APPLY_STATUS:
            held.append({"id": row_id, "status": status,
                         "notes": response.get("notes") or "",
                         "previous_status": row["status"]})
            continue
        target = response["target_ko"]
        if not isinstance(target, str) or not target.strip():
            problems.append({"id": row_id, "reason": "empty draft"})
            continue
        if TOKEN_RE.findall(target) != source["protected_tokens"]:
            problems.append({"id": row_id, "reason": "protected token changed",
                             "expected": source["protected_tokens"],
                             "found": TOKEN_RE.findall(target)})
            continue
        # Newlines are real here: the source strings contain them and the slot
        # holds them, so only reject a control character the source never used.
        stray_controls = [char for char in target
                          if ord(char) < 0x20 and char not in source["source_jp"]]
        if stray_controls:
            problems.append({"id": row_id, "reason": "control character not in source",
                             "found": [f"\\x{ord(char):02X}" for char in stray_controls]})
            continue
        try:
            encoded = encode_hangul(target)
        except ValueError as exc:
            problems.append({"id": row_id, "reason": f"codec: {exc}"})
            continue
        capacity = int(row["capacity_bytes"])
        if len(encoded) > capacity:
            problems.append({"id": row_id, "reason": "slot overflow",
                             "encoded_bytes": len(encoded), "capacity_bytes": capacity})
            continue
        applied.append({"id": row_id, "previous_status": row["status"],
                        "encoded_bytes": len(encoded), "capacity_bytes": capacity,
                        "before": row["target_ko"], "after": target})
        row["target_ko"] = target
        row["status"] = "translated"
        row["note"] = args.note

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(args.output)

    translated = sum(1 for row in rows if row["status"] == "translated")
    report = {
        "workbook": str(args.workbook),
        "input": str(args.input),
        "response": str(args.response),
        "output": str(args.output),
        "response_status": dict(counts),
        "applied": len(applied),
        "held": len(held),
        "problems": len(problems),
        "workbook_translated_rows": translated,
        "workbook_rows": len(rows),
        "previous_status_of_applied": dict(Counter(item["previous_status"]
                                                   for item in applied)),
        "held_by_status": dict(Counter(item["status"] for item in held)),
        "problem_sample": problems[:20],
        "held_sample": held[:20],
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in {"problem_sample", "held_sample"}},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

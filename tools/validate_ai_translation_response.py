#!/usr/bin/env python3
"""Validate an external AI response without merging it into the workbook."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from make_hangul_poc import encode_hangul


TOKEN_RE = re.compile(r"~[A-Za-z0-9][A-Za-z0-9]?|%[A-Za-z]")
FIELDS = {"id", "baseline", "target_ko", "status", "notes", "questions"}
ALLOWED_STATUS = {"draft", "needs_context", "needs_term_decision", "not_text_candidate"}


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise SystemExit(f"{path}:{line_number}: expected JSON object")
            value["_line"] = line_number
            rows.append(value)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_jsonl", type=Path)
    parser.add_argument("response_jsonl", type=Path)
    parser.add_argument("report_json", type=Path)
    args = parser.parse_args()

    source_rows = read_jsonl(args.input_jsonl)
    response_rows = read_jsonl(args.response_jsonl)
    source_by_id = {row["id"]: row for row in source_rows}
    response_ids = [row.get("id") for row in response_rows]
    duplicates = sorted(key for key, count in Counter(response_ids).items() if count > 1)
    source_ids = set(source_by_id)
    returned_ids = set(response_ids)
    errors: list[dict] = []
    warnings: list[dict] = []
    results: list[dict] = []

    if duplicates:
        errors.append({"kind": "duplicate_ids", "ids": duplicates})
    missing = sorted(source_ids - returned_ids)
    unknown = sorted((value for value in returned_ids - source_ids), key=lambda value: str(value))
    if missing:
        errors.append({"kind": "missing_ids", "ids": missing})
    if unknown:
        errors.append({"kind": "unknown_ids", "ids": unknown})

    for response in response_rows:
        row_id = response.get("id")
        if row_id not in source_by_id:
            continue
        source = source_by_id[row_id]
        item_errors = []
        item_warnings = []
        actual_fields = set(response) - {"_line"}
        if actual_fields != FIELDS:
            item_errors.append(
                {"kind": "response_fields", "expected": sorted(FIELDS), "actual": sorted(actual_fields)}
            )
        if response.get("baseline") != source["baseline"]:
            item_errors.append({"kind": "baseline_mismatch"})
        status = response.get("status")
        if status not in ALLOWED_STATUS:
            item_errors.append({"kind": "invalid_status", "value": status})
        target = response.get("target_ko")
        if not isinstance(target, str):
            item_errors.append({"kind": "target_not_string"})
            target = ""
        if status == "draft" and not target.strip():
            item_errors.append({"kind": "empty_draft"})
        if status != "draft" and target.strip():
            item_warnings.append({"kind": "target_present_for_non_draft_status"})
        if not isinstance(response.get("notes"), str):
            item_errors.append({"kind": "notes_not_string"})
        if not isinstance(response.get("questions"), list) or not all(
            isinstance(value, str) for value in response.get("questions", [])
        ):
            item_errors.append({"kind": "questions_not_string_list"})

        source_tokens = source["protected_tokens"]
        target_tokens = TOKEN_RE.findall(target)
        if status == "draft" and target_tokens != source_tokens:
            item_errors.append(
                {"kind": "protected_tokens", "expected": source_tokens, "actual": target_tokens}
            )

        encoded_bytes = None
        if status == "draft" and not item_errors:
            try:
                encoded_bytes = len(encode_hangul(target))
            except ValueError as exc:
                item_warnings.append({"kind": "unsupported_encoding", "detail": str(exc)})
            else:
                capacity = int(source["capacity_bytes"])
                if encoded_bytes > capacity:
                    item_warnings.append(
                        {
                            "kind": "current_slot_overflow",
                            "encoded_bytes": encoded_bytes,
                            "capacity_bytes": capacity,
                        }
                    )

        for issue in item_errors:
            errors.append({"id": row_id, "line": response["_line"], **issue})
        for issue in item_warnings:
            warnings.append({"id": row_id, "line": response["_line"], **issue})
        results.append(
            {
                "id": row_id,
                "status": status,
                "encoded_bytes": encoded_bytes,
                "capacity_bytes": source["capacity_bytes"],
                "error_count": len(item_errors),
                "warning_count": len(item_warnings),
            }
        )

    report = {
        "input": args.input_jsonl.name,
        "response": args.response_jsonl.name,
        "counts": {
            "expected": len(source_rows),
            "returned": len(response_rows),
            "errors": len(errors),
            "warnings": len(warnings),
            "status": dict(Counter(row.get("status") for row in response_rows)),
        },
        "valid_for_human_review": not errors,
        "note": "Mechanical validity does not approve translation quality or distribution eligibility.",
        "errors": errors,
        "warnings": warnings,
        "results": results,
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["counts"], ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

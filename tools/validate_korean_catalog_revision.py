#!/usr/bin/env python3
"""Validate prose-only revisions of this project's five public catalogs.

This checks identity, protected fields, tokens, numbers and codec round trips.
It does not approve meaning, font coverage, slot fit or in-game layout.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess

from make_hangul_poc import decode_hangul, encode_hangul
from text_control_guard import reject_new_ascii_tilde


CATALOGS = (
    "curated_batch_001.json",
    "curated_batch_002_bootflow.json",
    "curated_batch_003_nameflow.json",
    "development_draft_2026-09-24_ko_only.jsonl",
    "development_draft_2026-09-26_ko_only.jsonl",
)
TOKEN = re.compile(r"~[A-Za-z0-9][A-Za-z0-9]?|%(?:[-+ #0]*\d*(?:\.\d+)?[diuoxXfFeEgGaAcsp]|[A-Za-z])")
NUMBER = re.compile(r"\d+(?:[,./:]\d+)*%?")
PREFIX = re.compile(r"^(?:@|[|?]|[o*] )")
ROOT = Path(__file__).resolve().parents[1]


def parse(data: bytes, name: str) -> list[dict]:
    text = data.decode("utf-8-sig")
    rows = json.loads(text) if name.endswith(".json") else [json.loads(line) for line in text.splitlines() if line.strip()]
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{name}: expected a row catalog")
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{name}: duplicate IDs")
    return rows


def protected(text: str) -> dict:
    prefix = PREFIX.match(text)
    return {
        "tokens": TOKEN.findall(text),
        "numbers": NUMBER.findall(TOKEN.sub("", text)),
        "newlines": text.count("\n"),
        "leading_prefix": prefix.group(0) if prefix else "",
        "leading_spaces": len(text) - len(text.lstrip(" \t\n\r")),
        "trailing_spaces": len(text) - len(text.rstrip(" \t\n\r")),
    }


def compare(before: list[dict], after: list[dict], name: str, errors: list[dict], warnings: list[dict], label: str,
            original_by_id: dict[str, dict] | None = None) -> int:
    if [row["id"] for row in before] != [row["id"] for row in after]:
        errors.append({"file": name, "baseline": label, "kind": "ids_or_order_changed"})
        return 0
    field = "target" if name.endswith(".json") else "target_ko"
    changes = 0
    for old, new in zip(before, after):
        row_id = old["id"]
        if {k: v for k, v in old.items() if k != field} != {k: v for k, v in new.items() if k != field}:
            errors.append({"file": name, "baseline": label, "id": row_id, "kind": "protected_fields_changed"})
        target = new.get(field)
        if not isinstance(target, str) or not target.strip():
            errors.append({"file": name, "id": row_id, "kind": "empty_or_nonstring_target"})
            continue
        try:
            reject_new_ascii_tilde(old[field], target, row_id)
        except ValueError as exc:
            errors.append({'file':name,'baseline':label,'id':row_id,'kind':'introduced_ascii_tilde','detail':str(exc)})
        old_info, new_info = protected(old[field]), protected(target)
        for key in old_info:
            if old_info[key] == new_info[key]:
                continue
            restored = (key in {"newlines", "leading_spaces", "trailing_spaces"}
                        and original_by_id is not None and row_id in original_by_id
                        and protected(original_by_id[row_id][field])[key] == new_info[key])
            # Numerals can be spelled out in Korean; prefix markers can be
            # source bullets or scanner fragments. Flag them for prose review.
            destination = warnings if restored or key in {"numbers", "leading_prefix"} else errors
            destination.append({"file": name, "baseline": label, "id": row_id,
                                "kind": key + "_changed", "before": old_info[key], "after": new_info[key],
                                "restored_prior_structure": restored})
        if old[field] != target:
            changes += 1
    return changes


def audit(baseline_dir: Path, candidate_dir: Path, prior_ref: str | None = None) -> dict:
    errors, warnings, files = [], [], []
    shared = defaultdict(dict)
    total_rows = 0
    for name in CATALOGS:
        input_name = name.replace(".jsonl", "_polished.jsonl") if name.endswith(".jsonl") else name.replace(".json", "_polished.json")
        path = baseline_dir / input_name
        if not path.exists():
            path = baseline_dir / name
        before_data, after_data = path.read_bytes(), (candidate_dir / name).read_bytes()
        before, after = parse(before_data, name), parse(after_data, name)
        original = None
        original_changes = None
        if prior_ref:
            original_data = subprocess.check_output(["git", "show", f"{prior_ref}:translations/{name}"], cwd=ROOT)
            original = parse(original_data, name)
            original_changes = compare(original, after, name, errors, warnings, "prior_git_revision")
        changed = compare(before, after, name, errors, warnings, "user_polished_input",
                          {row["id"]: row for row in original} if original is not None else None)
        field = "target" if name.endswith(".json") else "target_ko"
        for row in after:
            target = row[field]
            shared[row["id"]][name] = target
            try:
                if decode_hangul(encode_hangul(target)) != target:
                    raise ValueError("codec round trip differs")
            except ValueError as exc:
                errors.append({"file": name, "id": row["id"], "kind": "encoding", "detail": str(exc)})
        total_rows += len(after)
        files.append({"file": name, "rows": len(after), "changed_from_user_input": changed,
                      "changed_from_prior_git": original_changes,
                      "input_sha256": hashlib.sha256(before_data).hexdigest(),
                      "output_sha256": hashlib.sha256(after_data).hexdigest()})
    for row_id, variants in shared.items():
        if len(set(variants.values())) > 1:
            warnings.append({"id": row_id, "kind": "cross_file_wording_conflict", "files": list(variants)})
    return {
        "schema_version": 1, "rows": total_rows, "catalogs": files,
        "errors": errors, "warnings": warnings, "mechanical_pass": not errors,
        "prior_git_revision": prior_ref,
        "scope": "Public catalog integrity and codec only; semantic, font, source-slot and runtime eligibility remain separate",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_dir", type=Path, help="Unmodified user input or baseline catalog directory")
    parser.add_argument("candidate_dir", type=Path)
    parser.add_argument("report_json", type=Path)
    parser.add_argument("--prior-ref", help="Optional Git baseline to check as well")
    args = parser.parse_args()
    report = audit(args.baseline_dir, args.candidate_dir, args.prior_ref)
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"rows": report["rows"], "errors": len(report["errors"]),
                      "warnings": len(report["warnings"]), "mechanical_pass": report["mechanical_pass"]}))
    if not report["mechanical_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

"""Validate a NEXT-PLUS mission JSONL response without approving its prose."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from make_hangul_poc import encode_hangul


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "work/next_plus_mission_handoff_v2"
FIELDS = {"id", "baseline", "target_ko", "status", "notes", "questions"}
STATUSES = {"pending", "draft", "needs_context", "needs_term_decision", "not_text_candidate"}
VARIABLE_RE = re.compile(r"%(?:\d+\$)?[-+ #0]*(?:\d+|\*)?(?:\.\d+)?[diuoxXfFeEgGcsp%]")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("response", nargs="?", type=Path, default=PACKAGE / "mission.response.jsonl")
    args = parser.parse_args()
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    input_path = PACKAGE / "mission.input.jsonl"
    if sha256_file(input_path) != manifest["input_sha256"]:
        raise ValueError("input package differs from its manifest")
    inputs = read_jsonl(input_path)
    responses = read_jsonl(args.response)
    if len(inputs) != manifest["translation_ready_records"] or len(responses) != len(inputs):
        raise ValueError("response count does not match the sealed input")
    errors: list[str] = []
    counts: Counter[str] = Counter()
    for source, response in zip(inputs, responses):
        row_id = source["id"]
        if set(response) != FIELDS:
            errors.append(f"{row_id}: response fields differ from the six-field contract")
            continue
        if response["id"] != row_id or response["baseline"] != source["baseline"]:
            errors.append(f"{row_id}: ID, order, or baseline changed")
            continue
        status = response["status"]
        if status not in STATUSES:
            errors.append(f"{row_id}: unknown status {status!r}")
            continue
        counts[status] += 1
        if not isinstance(response["notes"], str) or not isinstance(response["questions"], list):
            errors.append(f"{row_id}: malformed notes or questions")
            continue
        target = response["target_ko"]
        if not isinstance(target, str):
            errors.append(f"{row_id}: target_ko must be a string")
            continue
        if status == "draft" and not target:
            errors.append(f"{row_id}: draft is empty")
            continue
        if status == "pending" and target:
            errors.append(f"{row_id}: pending row has a filled target")
            continue
        if not target:
            continue
        if target.count("\n") != source["newline_count"] or not target.endswith("\n"):
            errors.append(f"{row_id}: must preserve three newline delimiters and final newline")
        if VARIABLE_RE.findall(target) != source["protected_tokens"]:
            errors.append(f"{row_id}: variable tokens changed order or value")
        if any(ord(char) < 0x20 and char != "\n" for char in target):
            errors.append(f"{row_id}: raw control character in target")
        try:
            encoded = b"".join(encode_hangul(line) + b"\n" for line in target[:-1].split("\n"))
        except ValueError as exc:
            errors.append(f"{row_id}: encoding: {exc}")
        else:
            if len(encoded) > source["capacity_bytes"]:
                errors.append(f"{row_id}: {len(encoded)} bytes exceed {source['capacity_bytes']}")
    report = {
        "input_sha256": manifest["input_sha256"],
        "response_sha256": sha256_file(args.response),
        "rows": len(responses),
        "status_counts": dict(counts),
        "error_count": len(errors),
        "errors": errors,
        "human_approved": False,
        "distributable": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

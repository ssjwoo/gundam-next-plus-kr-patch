"""Export Korean-only, unapproved EBOOT drafts for the public repository.

The local workbook contains source-language game text and binary metadata.
This exporter intentionally emits only stable row IDs and Korean draft text.
It does not mark translations approved or create a playable patch.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


ID_RE = re.compile(r"EBOOT_\d{5}\Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export(source: Path, output: Path, expected_count: int | None) -> dict[str, object]:
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"id", "status", "target_ko"}.issubset(reader.fieldnames or []):
            raise ValueError("missing required workbook columns")
        seen: set[str] = set()
        rows: list[dict[str, str]] = []
        for row in reader:
            row_id = row["id"]
            if not ID_RE.fullmatch(row_id) or row_id in seen:
                raise ValueError(f"invalid or duplicate ID: {row_id}")
            seen.add(row_id)
            if row["status"] != "translated":
                continue
            target = row["target_ko"]
            if not target or "\x00" in target:
                raise ValueError(f"empty or invalid Korean draft: {row_id}")
            rows.append({"id": row_id, "target_ko": target,
                         "review_state": "unapproved_draft"})
    if expected_count is not None and len(rows) != expected_count:
        raise ValueError(f"expected {expected_count} drafts, found {len(rows)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":"))
                              + "\n" for row in rows), encoding="utf-8")
    return {"rows": len(rows), "source_sha256": sha256_file(source),
            "output_sha256": sha256_file(output), "output": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_workbook", type=Path)
    parser.add_argument("output_jsonl", type=Path)
    parser.add_argument("--expected-count", type=int)
    args = parser.parse_args()
    print(json.dumps(export(args.source_workbook, args.output_jsonl,
                            args.expected_count), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

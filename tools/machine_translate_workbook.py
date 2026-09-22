#!/usr/bin/env python3
"""Create resumable Japanese->Korean machine drafts for workbook rows.

Machine output is never marked translated or approved.  Capacity, custom-codec
coverage and tag preservation are recorded so later human/independent QA has a
bounded queue rather than an unchecked corpus.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
import time
import unicodedata
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from make_hangul_poc import encode_hangul


TAG_RE = re.compile(r"~[A-Za-z][A-Za-z0-9]?")
NORMALIZE = str.maketrans(
    {
        "…": "...", "‥": "..", "・": " ", "·": "/", "×": "x",
        "“": '"', "”": '"', "‘": "'", "’": "'", "「": "[", "」": "]",
        "『": "[", "』": "]", "【": "[", "】": "]", "〜": "~", "～": "~",
        "→": "->", "←": "<-", "★": "*", "☆": "*", "※": "*",
    }
)


def protect_tags(text: str) -> tuple[str, list[str]]:
    tags = TAG_RE.findall(text)
    protected = text
    for index, tag in enumerate(tags):
        protected = protected.replace(tag, f"ZXQTAG{index}QXZ", 1)
    return protected, tags


def restore_tags(text: str, tags: list[str]) -> str:
    restored = text
    for index, tag in enumerate(tags):
        token = f"ZXQTAG{index}QXZ"
        # Translation services occasionally insert spaces around the digits.
        restored = re.sub(rf"ZXQTAG\s*{index}\s*QXZ", lambda _match: tag, restored)
    return restored


def normalize_target(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(NORMALIZE)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def translate(text: str, timeout: int) -> str:
    protected, tags = protect_tags(text)
    query = urlencode({"client": "gtx", "sl": "ja", "tl": "ko", "dt": "t", "q": protected})
    request = Request(
        "https://translate.googleapis.com/translate_a/single?" + query,
        headers={"User-Agent": "Mozilla/5.0 hanpatch-research"},
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    translated = "".join(segment[0] for segment in payload[0] if segment and segment[0])
    return normalize_target(restore_tags(translated, tags))


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("cache_json", type=Path)
    parser.add_argument("--evidence", default="fan_patch_modified")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--delay", type=float, default=0.08)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()
    with args.input_csv.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    cache = json.loads(args.cache_json.read_text(encoding="utf-8")) if args.cache_json.exists() else {}
    selected = [
        row for row in rows
        if row["evidence"] == args.evidence and not row["target_ko"]
    ]
    if args.limit:
        selected = selected[: args.limit]
    counts = {
        "selected": len(selected), "cache_hits": 0, "requests": 0, "fit": 0,
        "overflow": 0, "unsupported": 0, "tag_mismatch": 0, "errors": 0,
    }
    for ordinal, row in enumerate(selected, 1):
        source = row["source_jp"]
        try:
            if source in cache:
                target = cache[source]["target"]
                counts["cache_hits"] += 1
            else:
                last_error = None
                for attempt in range(3):
                    try:
                        target = translate(source, args.timeout)
                        last_error = None
                        break
                    except Exception as exc:
                        last_error = exc
                        time.sleep(0.5 * (attempt + 1))
                if last_error is not None:
                    raise last_error
                cache[source] = {"target": target, "provider": "google_translate_gtx", "source_lang": "ja", "target_lang": "ko"}
                counts["requests"] += 1
                atomic_json(args.cache_json, cache)
                time.sleep(args.delay)
            row["target_ko"] = target
            if TAG_RE.findall(source) != TAG_RE.findall(target):
                status = "machine_draft_tag_mismatch"
                counts["tag_mismatch"] += 1
            else:
                try:
                    encoded = encode_hangul(target)
                except ValueError as exc:
                    status = "machine_draft_unsupported"
                    row["note"] = str(exc)
                    counts["unsupported"] += 1
                else:
                    capacity = int(row["capacity_bytes"])
                    if len(encoded) > capacity:
                        status = "machine_draft_overflow"
                        row["note"] = f"{len(encoded)} encoded bytes > {capacity} byte slot"
                        counts["overflow"] += 1
                    else:
                        status = "machine_draft_fit"
                        counts["fit"] += 1
            row["status"] = status
        except Exception as exc:
            row["status"] = "machine_error"
            row["note"] = f"{type(exc).__name__}: {exc}"
            counts["errors"] += 1
        if ordinal % 20 == 0:
            write_csv(args.output_csv, fields, rows)
            print(json.dumps({"processed": ordinal, **counts}, ensure_ascii=True), flush=True)
    write_csv(args.output_csv, fields, rows)
    summary_path = args.output_csv.with_suffix(".summary.json")
    atomic_json(summary_path, counts)
    print(json.dumps(counts, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

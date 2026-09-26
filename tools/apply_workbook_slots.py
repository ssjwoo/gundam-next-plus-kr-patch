#!/usr/bin/env python3
"""Write workbook translations straight into the fixed text slots of a built ELF.

`build_korean_eboot.py` needs an inventory CSV that records each string's
original bytes (`raw_hex`).  That file is not kept in the tree, but every field
it needs is either in the workbook or derivable: the original bytes are the
source text encoded as CP932, which is exactly what the game stores.

The write itself follows the same rules the build script enforces:

  * the slot still holds the original source bytes,
  * the byte after them is a NUL,
  * everything up to ``capacity_bytes`` is zero,
  * the encoded Korean fits in ``capacity_bytes``.

Running it over the rows that are already applied must be a no-op, which is the
self-test that this reproduces the original pipeline.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_hangul_poc import encode_hangul  # noqa: E402

APPLY_STATUSES = {"translated", "approved"}


def decode_hangul(raw: bytes) -> str:
    """Inverse of encode_hangul: bytes below 0x80 are literal, 0x80+hi/0x80+lo
    pairs are syllables -- the same rule the patched decoder uses."""
    out = []
    cursor = 0
    while cursor < len(raw):
        byte = raw[cursor]
        if byte < 0x80:
            out.append(chr(byte))
            cursor += 1
            continue
        if cursor + 1 >= len(raw):
            break
        index = ((byte - 0x80) << 7) + (raw[cursor + 1] - 0x80)
        if not 0 <= index < 0x2BA4:
            break
        out.append(chr(0xAC00 + index))
        cursor += 2
    return "".join(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_elf", type=Path)
    parser.add_argument("translations_csv", type=Path)
    parser.add_argument("--output-elf", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--check-only", action="store_true",
                        help="verify the slots without writing an ELF")
    parser.add_argument("--restore-status", default="not_displayed",
                        help="rows with this status must keep the original bytes")
    parser.add_argument("--restore-source", type=Path,
                        help="original ELF to copy restored slots from")
    args = parser.parse_args()

    original = args.source_elf.read_bytes()
    with args.translations_csv.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    # Longest slot first, so a short string that sits inside a longer one never
    # clobbers the tail of the longer translation; the short one is refused.
    rows.sort(key=lambda row: (int(row["file_offset_hex"], 16), -int(row["capacity_bytes"])))

    patched = bytearray(original)
    original_elf = args.restore_source.read_bytes() if args.restore_source else None
    counts = {
        "rows": len(rows),
        "applied": 0,
        "already_applied": 0,
        "skipped_empty": 0,
        "skipped_status": 0,
        "over_capacity": 0,
        "source_mismatch": 0,
        "unsupported": 0,
        "restored": 0,
    }
    overflow: list[dict] = []
    mismatches: list[dict] = []

    for row in rows:
        # Some rows are binary tables rather than text.  The game reads them with
        # a fixed entry width, so they must stay byte-for-byte as shipped even
        # though an earlier pass translated them (the digit table at 0x28D3B4 is
        # read two bytes per digit and broke every "destroy N" objective).
        if row["status"] == args.restore_status and original_elf is not None:
            offset = int(row["file_offset_hex"], 16)
            span = int(row["capacity_bytes"]) + 1
            if patched[offset : offset + span] != original_elf[offset : offset + span]:
                patched[offset : offset + span] = original_elf[offset : offset + span]
                counts["restored"] += 1
            continue
        if row["status"] not in APPLY_STATUSES:
            counts["skipped_status"] += 1
            continue
        target = row["target_ko"]
        if not target:
            counts["skipped_empty"] += 1
            continue
        offset = int(row["file_offset_hex"], 16)
        capacity = int(row["capacity_bytes"])
        source_raw = row["source_jp"].encode("cp932")
        try:
            encoded = encode_hangul(target)
        except ValueError as exc:
            counts["unsupported"] += 1
            mismatches.append({"id": row["id"], "reason": f"unsupported: {exc}"})
            continue
        if len(encoded) > capacity:
            counts["over_capacity"] += 1
            overflow.append({"id": row["id"], "encoded": len(encoded), "capacity": capacity,
                             "target": target})
            continue

        span = capacity + 1
        current = bytes(patched[offset : offset + span])
        if current.startswith(encoded) and not any(current[len(encoded) :]):
            counts["already_applied"] += 1
            continue

        if not (bytes(patched[offset : offset + len(source_raw)]) == source_raw
                and patched[offset + len(source_raw)] == 0
                and not any(patched[offset + len(source_raw) + 1 : offset + span])):
            counts["source_mismatch"] += 1
            mismatches.append({
                "id": row["id"],
                "offset": hex(offset),
                "expected": source_raw.hex(" "),
                "found": bytes(patched[offset : offset + len(source_raw)]).hex(" "),
            })
            continue

        if not args.check_only:
            patched[offset : offset + span] = encoded + bytes(span - len(encoded))
        counts["applied"] += 1
        if decode_hangul(encoded) != target:
            raise AssertionError(
                f"{row['id']}: codec readback failed: {decode_hangul(encoded)!r} != {target!r}"
            )

    report = {
        "source_elf": str(args.source_elf),
        "translations_csv": str(args.translations_csv),
        "restore_source": str(args.restore_source) if args.restore_source else None,
        "check_only": args.check_only,
        "counts": counts,
        "overflow_sample": overflow[:20],
        "mismatch_sample": mismatches[:20],
    }

    if not args.check_only:
        if not args.output_elf:
            raise SystemExit("--output-elf is required unless --check-only")
        args.output_elf.parent.mkdir(parents=True, exist_ok=True)
        args.output_elf.write_bytes(bytes(patched))
        report["output_elf"] = str(args.output_elf)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in {"overflow_sample", "mismatch_sample"}},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

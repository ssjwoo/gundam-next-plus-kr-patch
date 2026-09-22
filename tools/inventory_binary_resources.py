#!/usr/bin/env python3
"""Classify non-PZZ Z_DATA records and MWo3 W_DATA overlays."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import struct

from inventory_eboot_text import KANA_RE, scan_strings
from unpack_pzz import xor_words


SIGNATURES = {
    b"MIG.00.1PSP\0": "GIM",
    b"PMF2": "PMF2",
    b"PGF0": "PGF",
    b"PSMF": "PSMF",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def xor_mode(blob: bytes) -> tuple[int, int]:
    words = struct.iter_unpack("<I", blob[: len(blob) & ~3])
    return Counter(word[0] for word in words).most_common(1)[0]


def signature_hits(blob: bytes) -> list[dict]:
    hits = []
    for signature, name in SIGNATURES.items():
        cursor = 0
        while True:
            offset = blob.find(signature, cursor)
            if offset < 0:
                break
            hits.append({"kind": name, "offset": offset})
            cursor = offset + 1
    return sorted(hits, key=lambda value: value["offset"])


def japanese_candidates(blob: bytes, source: str, container: str) -> list[dict]:
    section = {"offset": 0, "end": len(blob), "name": container, "address": 0}
    rows = []
    for item in scan_strings(blob, section, min_bytes=4):
        if item["category"] != "japanese" or not KANA_RE.search(item["text"]):
            continue
        rows.append(
            {
                "source": source,
                "container": container,
                "offset": item["file_offset"],
                "byte_length": item["byte_length"],
                "text": item["text"],
                "raw_hex": item["raw_hex"],
                "evidence": "printable_nul_terminated_cp932_with_kana_candidate",
            }
        )
    return rows


def inspect_z(path: Path) -> tuple[dict, list[dict]]:
    encrypted = path.read_bytes()
    key, frequency = xor_mode(encrypted)
    decoded = xor_words(encrypted, key)
    # All measured Z records carry a 16-byte non-structural-looking trailer;
    # retain it in the record and exclude it from string/signature scans.
    body = decoded[:-16] if len(decoded) >= 16 else decoded
    rows = japanese_candidates(body, str(path.resolve()), "Z_DATA_xor_decoded")
    return (
        {
            "path": str(path.resolve()),
            "name": path.name,
            "size": len(encrypted),
            "sha256": sha256(encrypted),
            "xor_key": f"0x{key:08X}",
            "xor_key_frequency": frequency,
            "xor_key_ratio": frequency / max(1, len(encrypted) // 4),
            "body_size": len(body),
            "trailer_size": len(decoded) - len(body),
            "decoded_head_32_hex": body[:32].hex(" "),
            "signature_hits": signature_hits(body),
            "japanese_candidate_count": len(rows),
        },
        rows,
    )


def inspect_w(path: Path) -> tuple[dict, list[dict]]:
    blob = path.read_bytes()
    rows = japanese_candidates(blob, str(path.resolve()), "W_DATA_MWo3")
    internal_name = ""
    if blob.startswith(b"MWo3") and len(blob) >= 0x30:
        internal_name = blob[0x20:0x30].split(b"\0", 1)[0].decode("ascii", "replace")
    return (
        {
            "path": str(path.resolve()),
            "name": path.name,
            "size": len(blob),
            "sha256": sha256(blob),
            "magic": blob[:4].decode("ascii", "replace"),
            "internal_name": internal_name,
            "signature_hits": signature_hits(blob),
            "japanese_candidate_count": len(rows),
        },
        rows,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("z_dir", type=Path)
    parser.add_argument("w_dir", type=Path)
    parser.add_argument("outdir", type=Path)
    args = parser.parse_args()
    z_records, w_records, candidates = [], [], []
    failures = []
    for path in sorted(args.z_dir.glob("*.bin")):
        try:
            record, rows = inspect_z(path)
            z_records.append(record)
            candidates.extend(rows)
        except Exception as exc:
            failures.append({"path": str(path.resolve()), "error": str(exc)})
    for path in sorted(args.w_dir.glob("*.bin")):
        try:
            record, rows = inspect_w(path)
            w_records.append(record)
            candidates.extend(rows)
        except Exception as exc:
            failures.append({"path": str(path.resolve()), "error": str(exc)})
    args.outdir.mkdir(parents=True, exist_ok=True)
    report = {
        "z_data_bin_files": len(z_records),
        "w_data_bin_files": len(w_records),
        "failures": failures,
        "z_signature_hit_files": sum(bool(row["signature_hits"]) for row in z_records),
        "w_signature_hit_files": sum(bool(row["signature_hits"]) for row in w_records),
        "japanese_candidates": len(candidates),
        "caveat": (
            "CP932 candidates in executable/gameplay binary records are leads only; "
            "they require renderer or reference evidence before classification as text."
        ),
        "z_records": z_records,
        "w_records": w_records,
    }
    (args.outdir / "binary_resource_inventory.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (args.outdir / "japanese_candidates.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        fields = ["source", "container", "offset", "byte_length", "text", "raw_hex", "evidence"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(candidates)
    summary = {key: value for key, value in report.items() if key not in {"z_records", "w_records"}}
    (args.outdir / "binary_resource_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

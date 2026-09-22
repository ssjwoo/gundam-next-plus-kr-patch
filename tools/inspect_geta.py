#!/usr/bin/env python3
"""Determine whether GETA.BIN carries payload or is disc-layout padding."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--chunk-size", type=int, default=8 * 1024 * 1024)
    args = parser.parse_args()

    digest = hashlib.sha256()
    total = 0
    zero_bytes = 0
    nonzero_chunks = []
    first_nonzero = None
    last_nonzero = None
    head = b""
    tail = b""
    with args.input.open("rb") as stream:
        chunk_index = 0
        while True:
            chunk = stream.read(args.chunk_size)
            if not chunk:
                break
            if not head:
                head = chunk[:64]
            tail = chunk[-64:]
            digest.update(chunk)
            zeros = chunk.count(0)
            zero_bytes += zeros
            if zeros != len(chunk):
                nonzero_chunks.append(chunk_index)
                if first_nonzero is None:
                    first_nonzero = total + next(
                        i for i, value in enumerate(chunk) if value != 0
                    )
                last_nonzero = total + len(chunk) - 1 - next(
                    i for i, value in enumerate(reversed(chunk)) if value != 0
                )
            total += len(chunk)
            chunk_index += 1

    report = {
        "path": str(args.input.resolve()),
        "size": total,
        "sha256": digest.hexdigest(),
        "zero_bytes": zero_bytes,
        "nonzero_bytes": total - zero_bytes,
        "all_zero": zero_bytes == total,
        "first_nonzero_offset": first_nonzero,
        "last_nonzero_offset": last_nonzero,
        "nonzero_chunk_count": len(nonzero_chunks),
        "chunk_size": args.chunk_size,
        "head_64_hex": head.hex(" "),
        "tail_64_hex": tail.hex(" "),
        "classification": (
            "zero-filled ISO layout/reserved-space file"
            if zero_bytes == total
            else "contains payload; further format analysis required"
        ),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

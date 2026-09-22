#!/usr/bin/env python3
"""Probe the per-file repeating XOR layer used by this game's PZZ assets."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct


SIGNATURES = {
    b"MIG.00.1PSP": "GIM",
    b"\x89PNG\r\n\x1a\n": "PNG",
    b"BM": "BMP",
    b"DDS ": "DDS",
    b"RIFF": "RIFF",
    b"OggS": "OGG",
    b"\x78\x01": "zlib-01",
    b"\x78\x9c": "zlib-9c",
    b"\x78\xda": "zlib-da",
}


def xor_words(blob: bytes, key: int) -> bytes:
    key_bytes = struct.pack("<I", key)
    return bytes(value ^ key_bytes[index & 3] for index, value in enumerate(blob))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    blob = args.input.read_bytes()
    words = struct.iter_unpack("<I", blob[: len(blob) & ~3])
    counts = Counter(word[0] for word in words)
    key, frequency = counts.most_common(1)[0]
    decoded = xor_words(blob, key)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(decoded)

    hits = []
    for signature, name in SIGNATURES.items():
        cursor = 0
        while True:
            offset = decoded.find(signature, cursor)
            if offset < 0:
                break
            hits.append({"signature": name, "offset": offset})
            cursor = offset + 1
    report = {
        "source": str(args.input.resolve()),
        "source_size": len(blob),
        "source_sha256": hashlib.sha256(blob).hexdigest(),
        "xor_key_le": f"0x{key:08X}",
        "key_frequency_dwords": frequency,
        "key_frequency_ratio": frequency / max(1, len(blob) // 4),
        "decoded": str(args.output.resolve()),
        "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
        "head_256_hex": decoded[:256].hex(" "),
        "signature_hits": sorted(hits, key=lambda hit: hit["offset"]),
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

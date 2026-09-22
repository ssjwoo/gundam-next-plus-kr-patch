#!/usr/bin/env python3
"""Unpack Gundam VS Gundam NEXT PLUS PZZ members.

Observed title-specific layout:
  * entire file XORed with one repeating little-endian 32-bit key;
  * decoded header at 0x000: LE u32 part count, then one LE u32 descriptor/part;
  * compressed blocks begin at 0x800 and each starts with two BE u32 values:
    zlib byte count and uncompressed byte count;
  * each next block is aligned to 0x80 bytes.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import zlib


def align(value: int, boundary: int) -> int:
    return (value + boundary - 1) & ~(boundary - 1)


def xor_words(blob: bytes, key: int) -> bytes:
    raw_key = struct.pack("<I", key)
    return bytes(value ^ raw_key[index & 3] for index, value in enumerate(blob))


def detect_xor_key(blob: bytes) -> int:
    """Recover the repeating key from encrypted zero-fill/padding words."""
    words = struct.iter_unpack("<I", blob[: len(blob) & ~3])
    key, _frequency = Counter(word[0] for word in words).most_common(1)[0]
    decoded_count = struct.unpack_from("<I", blob, 0)[0] ^ key
    if not 1 <= decoded_count <= 0x100:
        raise ValueError(
            f"XOR key candidate 0x{key:08X} gives implausible part count {decoded_count}"
        )
    return key


def sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("outdir", type=Path)
    args = parser.parse_args()

    encrypted = args.input.read_bytes()
    if len(encrypted) < 0x808:
        raise SystemExit("PZZ is too short")
    key = detect_xor_key(encrypted)
    decoded = xor_words(encrypted, key)
    count = struct.unpack_from("<I", decoded, 0)[0]
    if not 1 <= count <= 0x100:
        raise SystemExit(f"implausible part count {count}; XOR key assumption failed")
    descriptors = list(struct.unpack_from(f"<{count}I", decoded, 4))

    args.outdir.mkdir(parents=True, exist_ok=True)
    position = 0x800
    parts = []
    for index in range(count):
        descriptor = descriptors[index]
        flags = descriptor & 0xC0000000
        block_units = descriptor & 0x3FFFFFFF
        allocated_size = block_units * 0x80
        allocation_end = position + allocated_size
        if descriptor == 0:
            payload = b""
            compressed_size = None
            expected_size = 0
            storage = "empty"
            padding_bytes = 0
        elif allocation_end > len(decoded):
            raise SystemExit(
                f"part {index}: invalid allocation 0x{allocated_size:X} at 0x{position:X}"
            )
        elif flags & 0x40000000:
            if position + 8 > allocation_end:
                raise SystemExit(f"part {index}: truncated block header at 0x{position:X}")
            compressed_size, expected_size = struct.unpack_from(">II", decoded, position)
            data_start = position + 8
            data_end = data_start + compressed_size
            if data_end > allocation_end:
                raise SystemExit(
                    f"part {index}: compressed span ends past allocation at 0x{data_end:X}"
                )
            compressed = decoded[data_start:data_end]
            try:
                payload = zlib.decompress(compressed)
            except zlib.error as exc:
                raise SystemExit(f"part {index}: zlib failed at 0x{position:X}: {exc}") from exc
            if len(payload) != expected_size:
                raise SystemExit(
                    f"part {index}: expected {expected_size} bytes, decoded {len(payload)}"
                )
            storage = "zlib"
            padding_bytes = allocation_end - data_end
        else:
            compressed_size = None
            expected_size = allocated_size
            payload = decoded[position:allocation_end]
            storage = "raw"
            padding_bytes = 0
        output = args.outdir / f"part_{index:03d}.bin"
        output.write_bytes(payload)
        parts.append(
            {
                "index": index,
                "descriptor": descriptor,
                "descriptor_hex": f"0x{descriptor:08X}",
                "flags_hex": f"0x{flags:08X}",
                "storage": storage,
                "block_units": block_units,
                "allocated_size": allocated_size,
                "block_offset": position,
                "compressed_size": compressed_size,
                "uncompressed_size": expected_size,
                "padding_bytes": padding_bytes,
                "payload_sha256": sha256(payload),
                "head_32_hex": payload[:32].hex(" "),
                "output": str(output.resolve()),
            }
        )
        position = allocation_end

    trailing = decoded[position:]
    manifest = {
        "source": str(args.input.resolve()),
        "source_size": len(encrypted),
        "source_sha256": sha256(encrypted),
        "xor_key_le": f"0x{key:08X}",
        "part_count": count,
        "header_size": 0x800,
        "block_alignment": 0x80,
        "parts": parts,
        "consumed_to_aligned_offset": position,
        "trailing_bytes": len(trailing),
        "trailing_nonzero_bytes": sum(value != 0 for value in trailing),
        "trailing_hex": trailing.hex(" "),
    }
    (args.outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

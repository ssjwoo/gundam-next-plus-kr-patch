#!/usr/bin/env python3
"""Fixed-allocation PZZ repacker with payload readback verification.

The original 0x800-byte header, descriptor allocations, padding geometry and
16-byte trailer are retained.  A replacement is accepted only when it fits the
original part allocation, so the PZZ member never changes size.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib

from unpack_pzz import detect_xor_key, xor_words


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse(decoded: bytes) -> tuple[list[dict], int]:
    count = struct.unpack_from("<I", decoded, 0)[0]
    if not 1 <= count <= 0x100:
        raise ValueError(f"implausible part count {count}")
    descriptors = struct.unpack_from(f"<{count}I", decoded, 4)
    position = 0x800
    parts = []
    for index, descriptor in enumerate(descriptors):
        flags = descriptor & 0xC0000000
        units = descriptor & 0x3FFFFFFF
        allocated = units * 0x80
        end = position + allocated
        if descriptor == 0:
            payload = b""
            compressed_size = None
            capacity = 0
            storage = "empty"
        elif end > len(decoded):
            raise ValueError(f"part {index}: allocation runs past file")
        elif flags & 0x40000000:
            compressed_size, expected = struct.unpack_from(">II", decoded, position)
            data_end = position + 8 + compressed_size
            if data_end > end:
                raise ValueError(f"part {index}: compressed data runs past allocation")
            payload = zlib.decompress(decoded[position + 8 : data_end])
            if len(payload) != expected:
                raise ValueError(f"part {index}: size header/readback mismatch")
            capacity = allocated - 8
            storage = "zlib"
        else:
            payload = decoded[position:end]
            compressed_size = None
            capacity = allocated
            storage = "raw"
        parts.append(
            {
                "index": index,
                "descriptor": descriptor,
                "flags": flags,
                "units": units,
                "offset": position,
                "end": end,
                "allocated_size": allocated,
                "capacity": capacity,
                "storage": storage,
                "compressed_size": compressed_size,
                "payload": payload,
            }
        )
        position = end
    return parts, position


def best_zlib(payload: bytes) -> tuple[bytes, int]:
    candidates = [(zlib.compress(payload, level), level) for level in range(1, 10)]
    return min(candidates, key=lambda item: (len(item[0]), -item[1]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("replacements", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    encrypted = args.input.read_bytes()
    key = detect_xor_key(encrypted)
    decoded = bytearray(xor_words(encrypted, key))
    parts, consumed = parse(decoded)
    known_names = {f"part_{part['index']:03d}.bin" for part in parts}
    replacement_paths = {
        path.name: path
        for path in args.replacements.glob("part_*.bin")
        if path.is_file()
    } if args.replacements.exists() else {}
    extras = sorted(set(replacement_paths) - known_names)
    if extras:
        raise SystemExit(f"unknown replacement part(s): {', '.join(extras)}")

    changes = []
    expected_hashes = []
    for part in parts:
        name = f"part_{part['index']:03d}.bin"
        original_payload = part["payload"]
        replacement = replacement_paths.get(name)
        payload = replacement.read_bytes() if replacement else original_payload
        expected_hashes.append(sha256(payload))
        if payload == original_payload:
            continue
        if part["storage"] == "empty":
            raise SystemExit(f"{name}: an empty descriptor cannot accept a payload")
        start, end = part["offset"], part["end"]
        if part["storage"] == "raw":
            if len(payload) != part["allocated_size"]:
                raise SystemExit(
                    f"{name}: raw part must remain exactly {part['allocated_size']} bytes"
                )
            decoded[start:end] = payload
            compressed_size = None
            level = None
        else:
            compressed, level = best_zlib(payload)
            if len(compressed) > part["capacity"]:
                raise SystemExit(
                    f"{name}: compressed replacement {len(compressed)} exceeds "
                    f"fixed capacity {part['capacity']}"
                )
            decoded[start:end] = bytes(part["allocated_size"])
            struct.pack_into(">II", decoded, start, len(compressed), len(payload))
            decoded[start + 8 : start + 8 + len(compressed)] = compressed
            compressed_size = len(compressed)
        changes.append(
            {
                "part": part["index"],
                "storage": part["storage"],
                "allocated_size": part["allocated_size"],
                "old_payload_size": len(original_payload),
                "new_payload_size": len(payload),
                "old_payload_sha256": sha256(original_payload),
                "new_payload_sha256": sha256(payload),
                "new_compressed_size": compressed_size,
                "zlib_level": level,
            }
        )

    rebuilt = xor_words(bytes(decoded), key)
    if len(rebuilt) != len(encrypted):
        raise AssertionError("repacker changed PZZ size")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(rebuilt)

    # Read back from the produced artifact, not from the replacement directory.
    readback_key = detect_xor_key(rebuilt)
    readback_parts, readback_consumed = parse(xor_words(rebuilt, readback_key))
    actual_hashes = [sha256(part["payload"]) for part in readback_parts]
    if actual_hashes != expected_hashes:
        raise AssertionError("payload readback hash mismatch")
    if readback_consumed != consumed:
        raise AssertionError("readback allocation geometry mismatch")
    if not changes and rebuilt != encrypted:
        raise AssertionError("identity rebuild was not byte-exact")

    report = {
        "source": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "source_size": len(encrypted),
        "output_size": len(rebuilt),
        "source_sha256": sha256(encrypted),
        "output_sha256": sha256(rebuilt),
        "xor_key": f"0x{key:08X}",
        "part_count": len(parts),
        "changed_parts": changes,
        "identity_byte_exact": not changes and rebuilt == encrypted,
        "payload_readback_verified": True,
        "allocation_geometry_verified": True,
        "trailer_bytes_preserved": len(decoded) - consumed,
        "trailer_semantics": "unknown; original bytes retained",
    }
    report_path = args.report or args.output.with_suffix(args.output.suffix + ".json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

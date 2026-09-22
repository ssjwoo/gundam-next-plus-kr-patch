#!/usr/bin/env python3
"""Inventory every Gundam NEXT PLUS PZZ member without extracting payloads."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import struct
import zlib

from inspect_gim import gather, image_info, parse_chunk
from unpack_pzz import detect_xor_key, xor_words


def identify(payload: bytes) -> str:
    if not payload:
        return "EMPTY"
    if payload.startswith(b"MIG.00.1PSP\0"):
        return "GIM"
    if payload.startswith(b"PMF2"):
        return "PMF2"
    if payload.startswith(b"HITS"):
        return "HITS"
    if payload.startswith(b"SAD "):
        return "SAD"
    return "UNKNOWN"


def gim_summary(payload: bytes) -> dict:
    root = parse_chunk(payload, 16)
    pictures = gather(root, 3)
    entries = []
    for picture in pictures:
        images = [image_info(payload, child) for child in picture.children if child.type == 4]
        palettes = [image_info(payload, child) for child in picture.children if child.type == 5]
        entries.append(
            {
                "images": [
                    {
                        "width": value["width"],
                        "height": value["height"],
                        "format": value["format_name"],
                        "order": value["order_name"],
                        "bits_per_pixel": value["bits_per_pixel"],
                    }
                    for value in images
                ],
                "palettes": [
                    {
                        "entries": value["width"] * value["height"],
                        "format": value["format_name"],
                    }
                    for value in palettes
                ],
            }
        )
    return {"picture_count": len(pictures), "pictures": entries}


def inspect_pzz(path: Path) -> dict:
    encrypted = path.read_bytes()
    if len(encrypted) < 0x808:
        raise ValueError("file shorter than PZZ header plus first block header")
    key = detect_xor_key(encrypted)
    decoded = xor_words(encrypted, key)
    count = struct.unpack_from("<I", decoded, 0)[0]
    if not 1 <= count <= 0x100:
        raise ValueError(f"implausible part count {count}")
    descriptors = struct.unpack_from(f"<{count}I", decoded, 4)
    position = 0x800
    parts = []
    for index, descriptor in enumerate(descriptors):
        flags = descriptor & 0xC0000000
        block_units = descriptor & 0x3FFFFFFF
        allocated_size = block_units * 0x80
        allocation_end = position + allocated_size
        if descriptor == 0:
            compressed_size = None
            expected_size = 0
            payload = b""
            storage = "empty"
            padding_bytes = 0
        elif allocation_end > len(decoded):
            raise ValueError(f"part {index}: invalid allocation")
        elif flags & 0x40000000:
            if position + 8 > allocation_end:
                raise ValueError(f"part {index}: truncated block header")
            compressed_size, expected_size = struct.unpack_from(">II", decoded, position)
            data_start = position + 8
            data_end = data_start + compressed_size
            if data_end > allocation_end:
                raise ValueError(f"part {index}: compressed span past allocation")
            payload = zlib.decompress(decoded[data_start:data_end])
            if len(payload) != expected_size:
                raise ValueError(f"part {index}: expected {expected_size}, got {len(payload)}")
            storage = "zlib"
            padding_bytes = allocation_end - data_end
        else:
            compressed_size = None
            expected_size = allocated_size
            payload = decoded[position:allocation_end]
            storage = "raw"
            padding_bytes = 0
        kind = identify(payload)
        part = {
            "index": index,
            "descriptor": f"0x{descriptor:08X}",
            "flags": f"0x{flags:08X}",
            "storage": storage,
            "block_units": block_units,
            "allocated_size": allocated_size,
            "block_offset": position,
            "compressed_size": compressed_size,
            "uncompressed_size": expected_size,
            "padding_bytes": padding_bytes,
            "kind": kind,
            "head_16_hex": payload[:16].hex(" "),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        if kind == "GIM":
            part["gim"] = gim_summary(payload)
        parts.append(part)
        position = allocation_end
    trailing = decoded[position:]
    return {
        "path": str(path.resolve()),
        "name": path.name,
        "source_size": len(encrypted),
        "source_sha256": hashlib.sha256(encrypted).hexdigest(),
        "xor_key": f"0x{key:08X}",
        "part_count": count,
        "parts": parts,
        "consumed_to_aligned_offset": position,
        "trailing_bytes": len(trailing),
        "trailing_nonzero_bytes": sum(value != 0 for value in trailing),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("outdir", type=Path)
    args = parser.parse_args()
    paths = sorted(args.root.rglob("*.pzz"))
    records, failures = [], []
    kinds: Counter[str] = Counter()
    formats: Counter[str] = Counter()
    rows = []
    for ordinal, path in enumerate(paths, 1):
        try:
            record = inspect_pzz(path)
            records.append(record)
            for part in record["parts"]:
                kinds[part["kind"]] += 1
                gim = part.get("gim", {})
                pictures = gim.get("pictures", [])
                dimensions = []
                palette_specs = []
                for picture in pictures:
                    for image in picture["images"]:
                        formats[image["format"]] += 1
                        dimensions.append(f"{image['width']}x{image['height']}:{image['format']}:{image['order']}")
                    for palette in picture["palettes"]:
                        palette_specs.append(f"{palette['entries']}:{palette['format']}")
                rows.append(
                    {
                        "pzz_ordinal": ordinal,
                        "pzz_name": record["name"],
                        "pzz_size": record["source_size"],
                        "xor_key": record["xor_key"],
                        "part_index": part["index"],
                        "descriptor": part["descriptor"],
                        "storage": part["storage"],
                        "block_units": part["block_units"],
                        "allocated_size": part["allocated_size"],
                        "compressed_size": part["compressed_size"],
                        "uncompressed_size": part["uncompressed_size"],
                        "kind": part["kind"],
                        "gim_picture_count": gim.get("picture_count", ""),
                        "dimensions_formats": ";".join(dimensions),
                        "palettes": ";".join(palette_specs),
                        "payload_sha256": part["sha256"],
                        "path": record["path"],
                    }
                )
        except Exception as exc:
            failures.append({"path": str(path.resolve()), "error": str(exc)})
    args.outdir.mkdir(parents=True, exist_ok=True)
    report = {
        "root": str(args.root.resolve()),
        "pzz_files_found": len(paths),
        "pzz_files_parsed": len(records),
        "failures": failures,
        "payload_kinds": dict(sorted(kinds.items())),
        "gim_image_formats": dict(sorted(formats.items())),
        "records": records,
    }
    (args.outdir / "pzz_inventory.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (args.outdir / "pzz_parts.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["path"])
        writer.writeheader()
        writer.writerows(rows)
    summary = {key: value for key, value in report.items() if key != "records"}
    (args.outdir / "pzz_inventory_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

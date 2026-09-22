#!/usr/bin/env python3
"""Replace one indexed PSP GIM picture while preserving dimensions and palette."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from inspect_gim import gather, image_info, parse_chunk, read_indices, read_palette, render_picture


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode_indices(indexes: list[int], info: dict) -> bytes:
    width, height, fmt = info["width"], info["height"], info["format"]
    output = bytearray()
    if fmt not in (4, 5):
        raise ValueError(f"only Index4/Index8 are supported, got {info['format_name']}")
    if info["order"] == 1:
        block_width = 32 if fmt == 4 else 16
        if width % block_width or height % 8:
            raise ValueError("PSP-swizzled dimensions are not block aligned")
        for block_row in range(height // 8):
            for block_col in range(width // block_width):
                for pixel_row in range(8):
                    if fmt == 4:
                        for pixel_col in range(0, block_width, 2):
                            x = block_col * block_width + pixel_col
                            y = block_row * 8 + pixel_row
                            output.append(indexes[x + y * width] | (indexes[x + 1 + y * width] << 4))
                    else:
                        for pixel_col in range(block_width):
                            x = block_col * block_width + pixel_col
                            y = block_row * 8 + pixel_row
                            output.append(indexes[x + y * width])
    elif fmt == 5:
        output.extend(indexes)
    else:
        for offset in range(0, len(indexes), 2):
            second = indexes[offset + 1] if offset + 1 < len(indexes) else 0
            output.append(indexes[offset] | (second << 4))
    return bytes(output)


def distance(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    # Alpha errors are especially visible around antialiased glyph edges.
    return sum((a[i] - b[i]) ** 2 * (3 if i == 3 else 1) for i in range(4))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_gim", type=Path)
    parser.add_argument("picture", type=int)
    parser.add_argument("edited_png", type=Path)
    parser.add_argument("output_gim", type=Path)
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    original = args.input_gim.read_bytes()
    if not original.startswith(b"MIG.00.1PSP\0"):
        raise SystemExit("input is not a little-endian PSP GIM")
    root = parse_chunk(original, 16)
    pictures = gather(root, 3)
    if not 0 <= args.picture < len(pictures):
        raise SystemExit(f"picture index must be 0..{len(pictures) - 1}")
    picture = pictures[args.picture]
    image_chunks = [child for child in picture.children if child.type == 4]
    palette_chunks = [child for child in picture.children if child.type == 5]
    if len(image_chunks) != 1 or len(palette_chunks) != 1:
        raise SystemExit("replacement currently requires one image and one palette chunk")
    info = image_info(original, image_chunks[0])
    palette_info = image_info(original, palette_chunks[0])
    if info["format"] not in (4, 5):
        raise SystemExit(f"replacement requires indexed GIM, got {info['format_name']}")

    edited = Image.open(args.edited_png).convert("RGBA")
    expected_dimensions = (info["width"], info["height"])
    if edited.size != expected_dimensions:
        raise SystemExit(f"PNG is {edited.size}, expected {expected_dimensions}")
    palette = read_palette(original, palette_info)
    old_indexes = read_indices(original, info)
    old_pixels = [palette[index] for index in old_indexes]
    exact = {}
    for index, color in enumerate(palette):
        exact.setdefault(color, index)
    cache: dict[tuple[int, int, int, int], int] = {}
    new_indexes = []
    changed_pixels = 0
    quantized_pixels = 0
    for old_index, old_color, color in zip(old_indexes, old_pixels, edited.getdata()):
        if color == old_color:
            new_index = old_index
        elif color in exact:
            new_index = exact[color]
        else:
            if color not in cache:
                cache[color] = min(range(len(palette)), key=lambda index: distance(color, palette[index]))
            new_index = cache[color]
            quantized_pixels += 1
        new_indexes.append(new_index)
        if new_index != old_index:
            changed_pixels += 1

    encoded = encode_indices(new_indexes, info)
    expected_bytes = info["width"] * info["height"] * info["bits_per_pixel"] // 8
    if len(encoded) != expected_bytes:
        raise AssertionError(f"encoded {len(encoded)} bytes, expected {expected_bytes}")
    output = bytearray(original)
    start = info["first_image_offset"]
    output[start : start + len(encoded)] = encoded
    output_bytes = bytes(output)
    if len(output_bytes) != len(original):
        raise AssertionError("GIM size changed")

    palette_step = 4 if palette_info["format"] == 3 else 2
    palette_start = palette_info["first_image_offset"]
    palette_size = len(palette) * palette_step
    if output_bytes[palette_start : palette_start + palette_size] != original[palette_start : palette_start + palette_size]:
        raise AssertionError("palette bytes changed")
    # Independent structural readback of the output and optional visual preview.
    readback_root = parse_chunk(output_bytes, 16)
    readback_picture = gather(readback_root, 3)[args.picture]
    rendered = render_picture(output_bytes, readback_picture)
    if rendered.size != expected_dimensions:
        raise AssertionError("readback dimensions changed")
    if list(rendered.getdata()) != [palette[index] for index in new_indexes]:
        raise AssertionError("rendered readback pixels differ from encoded indices")

    args.output_gim.parent.mkdir(parents=True, exist_ok=True)
    args.output_gim.write_bytes(output_bytes)
    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        rendered.save(args.preview)
    report = {
        "source": str(args.input_gim.resolve()),
        "edited_png": str(args.edited_png.resolve()),
        "output": str(args.output_gim.resolve()),
        "picture": args.picture,
        "dimensions": list(expected_dimensions),
        "format": info["format_name"],
        "order": info["order_name"],
        "palette_entries": len(palette),
        "palette_format": palette_info["format_name"],
        "source_size": len(original),
        "output_size": len(output_bytes),
        "source_sha256": sha256(original),
        "output_sha256": sha256(output_bytes),
        "changed_index_pixels": changed_pixels,
        "pixels_mapped_to_nearest_palette_color": quantized_pixels,
        "palette_bytes_preserved": True,
        "dimensions_preserved": True,
        "readback_pixels_verified": True,
        "identity_byte_exact": changed_pixels == 0 and output_bytes == original,
    }
    report_path = args.report or args.output_gim.with_suffix(args.output_gim.suffix + ".json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

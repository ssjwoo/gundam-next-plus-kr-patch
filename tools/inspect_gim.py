#!/usr/bin/env python3
"""Inspect and render standard little-endian PSP GIM images."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
import struct

from PIL import Image


FORMAT_NAMES = {
    0: "RGBA5650",
    1: "RGBA5551",
    2: "RGBA4444",
    3: "RGBA8888",
    4: "Index4",
    5: "Index8",
    6: "Index16",
    7: "Index32",
    8: "DXT1",
    9: "DXT3",
    10: "DXT5",
    264: "DXT1EXT",
    265: "DXT3EXT",
    266: "DXT5EXT",
}
CHUNK_NAMES = {1: "block", 2: "file", 3: "picture", 4: "image", 5: "palette", 6: "sequence", 0xFF: "file_info"}


@dataclass
class Chunk:
    offset: int
    type: int
    args_offset: int
    next_offset: int
    child_offset: int
    data_offset: int
    children: list["Chunk"]


def parse_chunk(blob: bytes, offset: int) -> Chunk:
    if offset + 16 > len(blob):
        raise ValueError(f"truncated chunk header at 0x{offset:X}")
    typ, args, next_offset, child_offset, data_offset = struct.unpack_from(
        "<HHIII", blob, offset
    )
    if next_offset < 16 or offset + next_offset > len(blob):
        raise ValueError(f"invalid chunk size 0x{next_offset:X} at 0x{offset:X}")
    children = []
    cursor = offset + child_offset
    end = offset + next_offset
    while child_offset < next_offset and cursor + 16 <= end:
        child = parse_chunk(blob, cursor)
        children.append(child)
        cursor += child.next_offset
    return Chunk(offset, typ, args, next_offset, child_offset, data_offset, children)


def gather(chunk: Chunk, typ: int) -> list[Chunk]:
    out = [chunk] if chunk.type == typ else []
    for child in chunk.children:
        out.extend(gather(child, typ))
    return out


def image_info(blob: bytes, chunk: Chunk) -> dict:
    base = chunk.offset + chunk.data_offset
    values = struct.unpack_from("<12H5I4H", blob, base)
    keys = [
        "header_size", "unused", "format", "order", "width", "height",
        "bits_per_pixel", "pitch_align", "height_align", "dimension_count",
        "reserved", "reserved2", "offsets_offset", "images_offset", "total_size",
        "plane_mask", "level_type", "level_count", "frame_type", "frame_count",
    ]
    info = dict(zip(keys, values))
    info["format_name"] = FORMAT_NAMES.get(info["format"], f"unknown_{info['format']}")
    info["order_name"] = "PSP_swizzled" if info["order"] == 1 else "linear"
    info["chunk_offset"] = chunk.offset
    info["data_base"] = base
    if info["level_count"]:
        info["first_image_relative_offset"] = struct.unpack_from(
            "<I", blob, base + info["offsets_offset"]
        )[0]
        info["first_image_offset"] = base + info["first_image_relative_offset"]
    return info


def rgba_color(raw: bytes, offset: int, fmt: int) -> tuple[int, int, int, int]:
    if fmt == 3:
        return tuple(raw[offset : offset + 4])  # type: ignore[return-value]
    value = struct.unpack_from("<H", raw, offset)[0]
    if fmt == 0:
        r, g, b, a = (value & 31), ((value >> 5) & 63), ((value >> 11) & 31), 255
        return (r * 255 // 31, g * 255 // 63, b * 255 // 31, a)
    if fmt == 1:
        r, g, b, a = value & 31, (value >> 5) & 31, (value >> 10) & 31, (value >> 15) & 1
        return (r * 255 // 31, g * 255 // 31, b * 255 // 31, a * 255)
    if fmt == 2:
        r, g, b, a = value & 15, (value >> 4) & 15, (value >> 8) & 15, (value >> 12) & 15
        return (r * 17, g * 17, b * 17, a * 17)
    raise ValueError(f"unsupported direct color format {fmt}")


def read_indices(blob: bytes, info: dict) -> list[int]:
    width, height, fmt = info["width"], info["height"], info["format"]
    pos = info["first_image_offset"]
    indexes = [0] * (width * height)
    if fmt not in (4, 5):
        raise ValueError(f"indexed renderer does not support {info['format_name']}")
    if info["order"] == 1:
        block_width = 32 if fmt == 4 else 16
        storage_width = (width + block_width - 1) // block_width * block_width
        storage_height = (height + 7) // 8 * 8
        for block_row in range(storage_height // 8):
            for block_col in range(storage_width // block_width):
                for pixel_row in range(8):
                    if fmt == 4:
                        for pixel_col in range(0, block_width, 2):
                            value = blob[pos]
                            pos += 1
                            x = block_col * block_width + pixel_col
                            y = block_row * 8 + pixel_row
                            if y < height and x < width:
                                indexes[x + y * width] = value & 0x0F
                            if y < height and x + 1 < width:
                                indexes[x + 1 + y * width] = value >> 4
                    else:
                        for pixel_col in range(block_width):
                            x = block_col * block_width + pixel_col
                            y = block_row * 8 + pixel_row
                            if y < height and x < width:
                                indexes[x + y * width] = blob[pos]
                            pos += 1
    else:
        if fmt == 5:
            indexes[:] = blob[pos : pos + width * height]
        else:
            for i in range(0, width * height, 2):
                value = blob[pos]
                pos += 1
                indexes[i] = value & 0x0F
                if i + 1 < len(indexes):
                    indexes[i + 1] = value >> 4
    return indexes


def read_palette(blob: bytes, info: dict) -> list[tuple[int, int, int, int]]:
    count = info["width"] * info["height"]
    step = 4 if info["format"] == 3 else 2
    pos = info["first_image_offset"]
    return [rgba_color(blob, pos + index * step, info["format"]) for index in range(count)]


def render_picture(blob: bytes, picture: Chunk) -> Image.Image:
    images = [child for child in picture.children if child.type == 4]
    palettes = [child for child in picture.children if child.type == 5]
    if not images:
        raise ValueError("picture has no image chunk")
    info = image_info(blob, images[0])
    width, height, fmt = info["width"], info["height"], info["format"]
    if fmt in (4, 5):
        if not palettes:
            raise ValueError("indexed image has no palette chunk")
        palette = read_palette(blob, image_info(blob, palettes[0]))
        indexes = read_indices(blob, info)
        pixels = [palette[index] for index in indexes]
    elif fmt in (0, 1, 2, 3):
        step = 4 if fmt == 3 else 2
        pos = info["first_image_offset"]
        if info["order"] != 0:
            raise ValueError("direct-color PSP swizzle is not yet rendered")
        pixels = [rgba_color(blob, pos + index * step, fmt) for index in range(width * height)]
    else:
        raise ValueError(f"rendering {info['format_name']} is not yet supported")
    image = Image.new("RGBA", (width, height))
    image.putdata(pixels)
    return image


def inspect(path: Path, outdir: Path | None = None) -> dict:
    blob = path.read_bytes()
    if not blob.startswith(b"MIG.00.1PSP\0"):
        raise ValueError("not a little-endian PSP GIM")
    root = parse_chunk(blob, 16)
    pictures = gather(root, 3)
    entries = []
    for index, picture in enumerate(pictures):
        images = [image_info(blob, child) for child in picture.children if child.type == 4]
        palettes = [image_info(blob, child) for child in picture.children if child.type == 5]
        rendered = ""
        render_error = ""
        if outdir is not None:
            try:
                image = render_picture(blob, picture)
                outdir.mkdir(parents=True, exist_ok=True)
                output = outdir / f"picture_{index:03d}.png"
                image.save(output)
                rendered = str(output.resolve())
            except ValueError as exc:
                render_error = str(exc)
        entries.append(
            {
                "index": index,
                "chunk_offset": picture.offset,
                "images": images,
                "palettes": palettes,
                "rendered_png": rendered,
                "render_error": render_error,
            }
        )
    return {
        "source": str(path.resolve()),
        "size": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "picture_count": len(pictures),
        "pictures": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("outdir", type=Path)
    args = parser.parse_args()
    report = inspect(args.input, args.outdir)
    (args.outdir / "gim_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

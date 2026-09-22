#!/usr/bin/env python3
"""Render every GIM picture contained in one or more PZZ members."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from inspect_gim import gather, image_info, parse_chunk, render_picture
from repack_pzz import parse
from unpack_pzz import detect_xor_key, xor_words


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("outdir", type=Path)
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args()
    paths = []
    for supplied in args.inputs:
        if supplied.is_dir():
            paths.extend(sorted(supplied.rglob("*.pzz")))
        else:
            paths.append(supplied)
    records = []
    for path in paths:
        encrypted = path.read_bytes()
        key = detect_xor_key(encrypted)
        parts, _consumed = parse(xor_words(encrypted, key))
        destination = args.outdir / path.stem
        images = []
        for part in parts:
            payload = part["payload"]
            if not payload.startswith(b"MIG.00.1PSP\0"):
                continue
            root = parse_chunk(payload, 16)
            for picture_index, picture in enumerate(gather(root, 3)):
                image_chunks = [child for child in picture.children if child.type == 4]
                info = image_info(payload, image_chunks[0]) if image_chunks else {}
                try:
                    image = render_picture(payload, picture)
                    destination.mkdir(parents=True, exist_ok=True)
                    output = destination / f"part_{part['index']:03d}_picture_{picture_index:03d}.png"
                    image.save(output)
                    error = ""
                except ValueError as exc:
                    output = None
                    error = str(exc)
                images.append(
                    {
                        "part": part["index"],
                        "picture": picture_index,
                        "width": info.get("width"),
                        "height": info.get("height"),
                        "format": info.get("format_name"),
                        "output": str(output.resolve()) if output else "",
                        "error": error,
                    }
                )
        records.append({"source": str(path.resolve()), "images": images})
    args.outdir.mkdir(parents=True, exist_ok=True)
    manifest = {"sources": len(paths), "records": records}
    (args.outdir / "render_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"sources": len(paths), "images": sum(len(r["images"]) for r in records)}, ensure_ascii=True))


if __name__ == "__main__":
    main()

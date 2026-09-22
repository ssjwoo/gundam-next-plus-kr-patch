#!/usr/bin/env python3
"""Strip the 0x40-byte ~SCE wrapper from a PSP PRX for analysis."""

from __future__ import annotations

import argparse
import gzip
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--gunzip",
        action="store_true",
        help="decompress a gzip payload instead of stripping a ~SCE wrapper",
    )
    args = parser.parse_args()

    data = args.input.read_bytes()
    if args.gunzip:
        if data[:2] != b"\x1f\x8b":
            raise SystemExit("input is not a gzip stream")
        args.output.write_bytes(gzip.decompress(data))
        return
    if data[:4] != b"~SCE" or data[0x40:0x44] != b"~PSP":
        raise SystemExit("input is not a ~SCE-wrapped ~PSP module")
    args.output.write_bytes(data[0x40:])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Read-only PSP ISO9660 extractor using hanpatch's validated extent reader."""

from __future__ import annotations

import argparse
from pathlib import Path

from hanpatch.platforms.psp import iso9660


CHUNK = 8 * 1024 * 1024


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("paths", nargs="*", help="ISO paths; omit to extract all files")
    args = parser.parse_args()
    wanted = {("/" + item.strip("/")).upper() for item in args.paths}
    extracted = 0
    with iso9660.Iso.from_path(args.image) as iso:
        for entry in iso.walk():
            if entry.is_dir or (wanted and entry.path.upper() not in wanted):
                continue
            target = args.out / entry.path.lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                at = entry.offset
                end = at + entry.size
                while at < end:
                    nxt = min(at + CHUNK, end)
                    handle.write(iso.blob[at:nxt])
                    at = nxt
            extracted += 1
            print(f"{entry.path}\t{entry.size}\t{target}")
    if wanted and extracted != len(wanted):
        raise SystemExit(f"requested {len(wanted)} files, extracted {extracted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

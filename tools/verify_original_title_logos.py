#!/usr/bin/env python3
"""Enforce the user's original-title-logo policy against native ISO/PZZ pixels."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from hanpatch.platforms.psp import iso9660

from inspect_gim import gather, parse_chunk, render_picture
from pzz_integrity import verify_trailer
from repack_pzz import parse
from unpack_pzz import detect_xor_key, xor_words

DEFAULT_POLICY = Path(__file__).resolve().parents[1] / 'translations/graphics/original_gundam_title_logos.json'


def verify_records(policy, read_member):
    assert policy['action'] == 'preserve_original_title_logos'
    cache = {}
    for row in policy['records']:
        name = row['asset']
        if name not in cache:
            raw = read_member(row)
            assert len(raw) == row['pzz_bytes']
            decoded = xor_words(raw, detect_xor_key(raw))
            parts, end = parse(decoded)
            assert end == len(raw) - 16 and verify_trailer(raw, decoded)
            cache[name] = parts
        payload = cache[name][row['part']]['payload']
        picture = gather(parse_chunk(payload, 16), 3)[row['picture']]
        pixels = np.array(render_picture(payload, picture).convert('RGBA'))
        assert [pixels.shape[1], pixels.shape[0]] == row['dimensions']
        keep = np.zeros(pixels.shape[:2], dtype=bool)
        for x0, y0, x1, y1 in row['retained_ui_rectangles']:
            assert 0 <= x0 < x1 <= pixels.shape[1] and 0 <= y0 < y1 <= pixels.shape[0]
            keep[y0:y1, x0:x1] = True
        digest = hashlib.sha256(pixels[~keep].tobytes()).hexdigest()
        assert digest == row['protected_source_rgba_sha256'], f'Original title logo policy failed: {name} part {row["part"]} picture {row["picture"]}'
    return {'policy': 'preserve_original_title_logos', 'protected_members': len(cache),
            'protected_surfaces': len(policy['records']), 'verdict': 'PASS'}


def verify_iso(path, policy_path=DEFAULT_POLICY):
    policy = json.loads(policy_path.read_text(encoding='utf-8'))
    with iso9660.Iso.from_path(path) as iso:
        return verify_records(policy, lambda row: bytes(iso.blob[row['iso_absolute_offset']:row['iso_absolute_offset'] + row['pzz_bytes']]))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('iso', type=Path)
    p.add_argument('--policy', type=Path, default=DEFAULT_POLICY)
    args = p.parse_args()
    print(json.dumps(verify_iso(args.iso, args.policy)))


if __name__ == '__main__':
    main()

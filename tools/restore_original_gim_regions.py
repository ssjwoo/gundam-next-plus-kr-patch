#!/usr/bin/env python3
"""Restore source GIM indices exactly, retaining explicitly selected current pixels.

The input plan binds original and current PZZ hashes. No color quantization or
image synthesis is used. Output members retain all unrelated parts and pictures.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image

from inspect_gim import gather, image_info, parse_chunk, read_indices, read_palette, render_picture
from pzz_integrity import checksum_trailer, verify_trailer
from repack_pzz import best_zlib, parse
from replace_gim_picture import encode_indices
from unpack_pzz import detect_xor_key, xor_words


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def unpack(raw):
    key = detect_xor_key(raw)
    decoded = xor_words(raw, key)
    parts, end = parse(decoded)
    assert end == len(raw) - 16 and verify_trailer(raw, decoded)
    return key, decoded, parts


def retention_mask(record, size):
    mask = np.zeros((size[1], size[0]), dtype=bool)
    if record.get('keep_mask'):
        image = Image.open(record['keep_mask']).convert('L')
        assert image.size == size
        mask |= np.array(image) > 0
    for x0, y0, x1, y1 in record.get('keep_boxes', []):
        assert 0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]
        mask[y0:y1, x0:x1] = True
    return mask


def restore_picture(original, current, record):
    old_pictures = gather(parse_chunk(original, 16), 3)
    now_pictures = gather(parse_chunk(current, 16), 3)
    assert len(old_pictures) == len(now_pictures)
    index = record['picture']
    a, b = old_pictures[index], now_pictures[index]
    assert (a.offset, a.next_offset) == (b.offset, b.next_offset)
    source_image = render_picture(original, a).convert('RGBA')
    current_image = render_picture(current, b).convert('RGBA')
    assert source_image.size == current_image.size
    source_rgba, current_rgba = np.array(source_image), np.array(current_image)
    assert sha(source_rgba.tobytes()) == record['source_picture_sha256']
    assert sha(current_rgba.tobytes()) == record['baseline_picture_sha256']
    keep = retention_mask(record, source_image.size)
    result = bytearray(current)
    if record['operation'] == 'whole_original_picture':
        assert not keep.any()
        result[a.offset:a.offset + a.next_offset] = original[a.offset:a.offset + a.next_offset]
    else:
        source_info = image_info(original, next(c for c in a.children if c.type == 4))
        current_info = image_info(current, next(c for c in b.children if c.type == 4))
        assert source_info == current_info
        assert source_info['level_count'] == source_info['frame_count'] == 1
        source_palette = read_palette(original, image_info(original, next(c for c in a.children if c.type == 5)))
        current_palette = read_palette(current, image_info(current, next(c for c in b.children if c.type == 5)))
        assert source_palette == current_palette
        source_indices = np.array(read_indices(original, source_info))
        current_indices = np.array(read_indices(current, current_info))
        wanted = np.where(keep.ravel(), current_indices, source_indices)
        encoded = encode_indices(wanted.tolist(), current_info)
        start = current_info['first_image_offset']
        result[start:start + len(encoded)] = encoded
        actual_indices = np.array(read_indices(result, current_info))
        assert np.array_equal(actual_indices, wanted)
        assert result[:start] == current[:start] and result[start + len(encoded):] == current[start + len(encoded):]
    result = bytes(result)
    rebuilt_pictures = gather(parse_chunk(result, 16), 3)
    actual = np.array(render_picture(result, rebuilt_pictures[index]))
    assert np.array_equal(actual[~keep], source_rgba[~keep])
    assert np.array_equal(actual[keep], current_rgba[keep])
    for n, (old, new) in enumerate(zip(now_pictures, rebuilt_pictures)):
        if n != index:
            assert result[new.offset:new.offset + new.next_offset] == current[old.offset:old.offset + old.next_offset]
    assert len(result) == len(current)
    return result, {
        'part': record['part'], 'picture': index, 'dimensions': list(source_image.size),
        'protected_source_pixel_match': True, 'retained_korean_pixel_match': True,
        'restored_rgba_sha256': sha(actual.tobytes()),
        'changed_pixels': int(np.count_nonzero(np.any(actual != current_rgba, axis=2))),
        'other_pictures_byte_exact': True, 'palette_and_geometry_preserved': True,
    }


def rebuild_pzz(current, replacements):
    key, decoded, parts = unpack(current)
    rebuilt = bytearray(decoded)
    for part in parts:
        payload = replacements.get(part['index'], part['payload'])
        if payload == part['payload']:
            continue
        assert len(payload) == len(part['payload'])
        start, end = part['offset'], part['end']
        if part['storage'] == 'raw':
            assert len(payload) == part['allocated_size']
            rebuilt[start:end] = payload
        else:
            assert part['storage'] == 'zlib'
            compressed, _ = best_zlib(payload)
            assert len(compressed) <= part['capacity']
            rebuilt[start:end] = bytes(part['allocated_size'])
            struct.pack_into('>II', rebuilt, start, len(compressed), len(payload))
            rebuilt[start + 8:start + 8 + len(compressed)] = compressed
    result = xor_words(rebuilt, key)
    result = result[:-16] + checksum_trailer(rebuilt[:-16])
    new_key, new_decoded, new_parts = unpack(result)
    assert new_key == key and new_decoded[:0x800] == decoded[:0x800]
    for a, b in zip(parts, new_parts):
        assert (a['offset'], a['end'], a['storage']) == (b['offset'], b['end'], b['storage'])
        assert b['payload'] == replacements.get(a['index'], a['payload'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('current_members', type=Path)
    parser.add_argument('output_members', type=Path)
    parser.add_argument('--resume', action='store_true', help='Verify and reuse byte-exact outputs from an interrupted run')
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding='utf-8'))['records']
    assert len({r['asset'] for r in plan}) == len(plan)
    if args.output_members.exists():
        assert args.resume, 'Use a fresh output directory or --resume'
        assert all(p.is_file() and p.name in {r['asset'] for r in plan} for p in args.output_members.iterdir())
    args.output_members.mkdir(parents=True, exist_ok=args.resume)
    records = []
    for r in plan:
        source = Path(r['source_path']).read_bytes()
        current = (args.current_members / r['asset']).read_bytes()
        assert sha(source) == r['source_pzz_sha256']
        assert sha(current) == r['baseline_pzz_sha256']
        _, _, source_parts = unpack(source)
        _, _, current_parts = unpack(current)
        assert len(source_parts) == len(current_parts)
        receipts = []
        if r['operation'] == 'whole_original_pzz':
            result = source
            for a, b in zip(source_parts, current_parts):
                if not a['payload'].startswith(b'MIG.00.1PSP'):
                    assert a['payload'] == b['payload'], 'Unexpected non-image source rollback'
        else:
            part = r['part']
            payload, receipt = restore_picture(source_parts[part]['payload'], current_parts[part]['payload'], r)
            receipts.append(receipt)
            result = rebuild_pzz(current, {part: payload})
        assert len(result) == len(source) == len(current) and result != current
        target = args.output_members / r['asset']
        if target.exists():
            assert args.resume and target.read_bytes() == result, 'Interrupted output differs from recomputed result'
        else:
            target.write_bytes(result)
        assert target.read_bytes() == result
        records.append({'asset': r['asset'], 'category': r['category'], 'regions': r['regions'],
                        'source_sha256': sha(source), 'baseline_sha256': sha(current),
                        'output_sha256': sha(result), 'whole_member_source_exact': result == source,
                        'surfaces': receipts, 'loader_checksum_verified': True})
    report = {'records': records, 'members': len(records),
              'reverted_logo_regions': sum(r['regions'] for r in records),
              'static_verdict': 'PASS', 'runtime_verdict': 'NOT_TESTED'}
    args.output_members.with_suffix('.report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'records'}))


if __name__ == '__main__':
    main()

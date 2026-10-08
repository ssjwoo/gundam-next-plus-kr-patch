"""Rebuild supervisor-authored fixed-size texture edits from private native bindings.

The public recipe contains Korean labels and hashes, not game asset pixels.
Baseline ISO, packet PNG/GIM bindings, font and AFS inventory stay local.
This only verifies static native readback; mode/runtime approval is separate.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = None
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'work/dependencies/hanpatch')]
from inspect_gim import gather, parse_chunk, render_picture
from repack_pzz import parse
from unpack_pzz import detect_xor_key, xor_words
from pzz_integrity import verify_trailer
from hanpatch.platforms.psp.iso9660 import Iso

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def call(tool, *args):
    p = subprocess.run([sys.executable, str(ROOT / 'tools' / tool), *map(str, args)], cwd=ROOT,
                       capture_output=True, text=True, encoding='utf-8')
    if p.returncode:
        raise RuntimeError(p.stdout + p.stderr)

def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recipe', type=Path)
    parser.add_argument('baseline_iso', type=Path)
    parser.add_argument('inventory', type=Path)
    parser.add_argument('font', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    authored = json.loads(args.recipe.read_bytes())
    OUT = args.output.resolve()
    if OUT.exists():
        parser.error('Use a fresh output directory; prior stages are immutable')
    with args.baseline_iso.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == authored['baseline_iso_sha256']
    assert sha(args.font.read_bytes()) == authored['font_file_sha256']
    assert len({r['image_id'] for r in authored['images']}) == len(authored['images'])
    batches = {}
    grouped = defaultdict(list)
    for item in authored['images']:
        packet = ROOT / item['packet']
        if str(packet) not in batches:
            binding_bytes = (packet / 'IMAGE_BINDINGS.private.json').read_bytes()
            assert sha(binding_bytes) == authored['packet_bindings_sha256'][item['packet']]
            batches[str(packet)] = json.loads(binding_bytes)
        b = next(r for r in batches[str(packet)]['images'] if r['image_id'] == item['image_id'])
        m = next(r for r in batches[str(packet)]['members'] if r['member'] == b['member'])
        grouped[b['member']].append((item, b, m))
    inventory = json.loads(args.inventory.read_bytes())
    font = args.font
    receipts, sources = [], []
    baseline = args.baseline_iso
    with Iso.from_path(baseline) as iso:
        for member, items in grouped.items():
            meta = items[0][2]
            raw = bytes(iso.blob[meta['iso_absolute_offset']:meta['iso_absolute_offset'] + meta['size']])
            assert sha(raw) == meta['current039_member_sha256']
            folder = OUT / 'members' / Path(member).stem
            folder.mkdir(parents=True, exist_ok=True)
            source = folder / member; source.write_bytes(raw)
            parts, _ = parse(xor_words(raw, detect_xor_key(raw)))
            bypart = defaultdict(list)
            for item, b, m in items:
                assert m == meta
                bypart[b['part']].append((item, b))
            replacements = folder / 'replacement_parts'; replacements.mkdir(exist_ok=True)
            for part, pictures in bypart.items():
                gim = parts[part]['payload']
                old_chunks = gather(parse_chunk(gim, 16), 3)
                changed = {}
                current = gim
                for item, b in pictures:
                    png = Path(b['current039_png']); original = Path(b['original_png'])
                    assert sha(png.read_bytes()) == b['current039_png_sha256']
                    assert sha(original.read_bytes()) == b['original_png_sha256']
                    source_image = render_picture(gim, old_chunks[b['picture']]).convert('RGBA')
                    assert sha(source_image.tobytes()) == b['current039_rgba_sha256']
                    assert source_image.tobytes() == Image.open(png).convert('RGBA').tobytes()
                    assert sha(Image.open(original).convert('RGBA').tobytes()) == b['original_rgba_sha256']
                    tag = b['image_id']
                    input_gim = folder / f'{tag}_input.gim'; input_gim.write_bytes(current)
                    identity = folder / f'{tag}_identity.gim'
                    call('replace_gim_picture.py', input_gim, b['picture'], png, identity,
                         '--report', folder / f'{tag}_identity.private.json')
                    assert identity.read_bytes() == current
                    rules = {'asset': f'{member}/part_{part:03}/picture_{b["picture"]:03}',
                             'dimensions': b['dimensions'], 'labels': item['labels']}
                    rules_path = folder / f'{tag}_rules.private.json'; write(rules_path, rules)
                    edited = folder / f'{tag}_edited.png'
                    call('render_localized_labels.py', png, rules_path, font, edited,
                         '--expected-source-sha256', sha(png.read_bytes()), '--expected-font-sha256', sha(font.read_bytes()))
                    output_gim = folder / f'{tag}_output.gim'; readback = folder / f'{tag}_readback.png'
                    call('replace_gim_picture.py', input_gim, b['picture'], edited, output_gim,
                         '--preview', readback, '--report', folder / f'{tag}_gim.private.json')
                    decoded = np.array(Image.open(readback).convert('RGBA')); before = np.array(source_image)
                    mask = np.zeros(before.shape[:2], dtype=bool)
                    for label in item['labels']:
                        x0, y0, x1, y1 = label['box']; mask[y0:y1, x0:x1] = True
                    diff = np.any(decoded != before, axis=2)
                    assert np.any(diff) and not np.any(diff & ~mask), ('Protected pixels changed', tag)
                    assert b['picture'] not in changed
                    changed[b['picture']] = (mask, decoded)
                    current = output_gim.read_bytes()
                    receipts.append({'image_id': tag, 'asset': member, 'part': part, 'picture': b['picture'],
                        'labels': item['labels'], 'supervisor_reason': item['reason'], 'before_rgba_sha256': sha(source_image.tobytes()),
                        'after_rgba_sha256': sha(decoded.tobytes()), 'changed_pixels': int(diff.sum()), 'protected_pixels_changed': 0,
                        'identity_roundtrip': 'BYTE_EXACT_PASS', 'mode_binding': b['mode_binding'],
                        'review_state': 'supervisor_reviewed_development', 'runtime_verdict': 'NOT_TESTED'})
                new_chunks = gather(parse_chunk(current, 16), 3)
                assert len(old_chunks) == len(new_chunks)
                for picture, (o, n) in enumerate(zip(old_chunks, new_chunks)):
                    before = np.array(render_picture(gim, o).convert('RGBA'))
                    after = np.array(render_picture(current, n).convert('RGBA'))
                    if picture in changed:
                        mask, decoded = changed[picture]
                        assert np.array_equal(after, decoded) and not np.any(np.any(before != after, axis=2) & ~mask)
                    else:
                        assert np.array_equal(before, after)
                (replacements / f'part_{part:03}.bin').write_bytes(current)
            outputs = OUT / 'replacements'; outputs.mkdir(exist_ok=True)
            out_pzz = outputs / member
            call('repack_pzz.py', source, replacements, out_pzz, '--report', folder / 'pzz.private.json')
            rebuilt = out_pzz.read_bytes(); decoded = xor_words(rebuilt, detect_xor_key(rebuilt))
            assert len(rebuilt) == len(raw) and verify_trailer(rebuilt, decoded)
            newparts, _ = parse(decoded); assert len(newparts) == len(parts)
            for old, new in zip(parts, newparts):
                assert (old['offset'], old['end'], old['storage']) == (new['offset'], new['end'], new['storage'])
                if old['index'] not in bypart:
                    assert old['payload'] == new['payload']
                else:
                    assert new['payload'] == (replacements / f'part_{old["index"]:03}.bin').read_bytes()
            entry = next(r for r in inventory['records'] if r['name'] == member)
            assert entry['iso_absolute_offset'] == meta['iso_absolute_offset'] and entry['size'] == meta['size']
            sources.append({**entry, 'sha256': sha(raw)})
            print(json.dumps({'asset': member, 'pictures': len(items), 'static_verdict': 'PASS'}), flush=True)
    # Merge sequential stages only after each member has fully verified readback.
    receipt_path = OUT / 'graphics_check.private.json'
    if receipt_path.exists():
        prior = json.loads(receipt_path.read_bytes())
        assert not set(r['image_id'] for r in prior['images']) & set(r['image_id'] for r in receipts)
        receipts = prior['images'] + receipts
    source_path = OUT / 'source_manifest.private.json'
    if source_path.exists():
        prior = json.loads(source_path.read_bytes())['records']
        assert not set(r['name'] for r in prior) & set(r['name'] for r in sources)
        sources = prior + sources
    write(receipt_path, {'baseline_revision': authored['baseline_revision'], 'images': receipts, 'protected_native_pixels_changed': 0,
                        'other_gim_pictures_and_pzz_parts_preserved': True, 'static_verdict': 'PASS', 'runtime_verdict': 'NOT_TESTED'})
    write(source_path, {'records': sources})
    print(json.dumps({'total_images': len(receipts), 'total_members': len(sources), 'static_verdict': 'PASS'}))

if __name__ == '__main__':
    main()

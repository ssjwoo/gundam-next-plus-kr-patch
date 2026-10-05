#!/usr/bin/env python3
"""Apply a compiled fixed-slot .data plan, verifying all other disc bytes.

Private build only. The source ISO is read for hash verification; no emulator
or game entry is run. Use prepare_residual_text_plan.py for source bindings and
glyph checks. Existing outputs are refused.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import zlib

from elftools.elf.elffile import ELFFile
from hanpatch.platforms.psp import iso9660
from make_hangul_poc import decode_hangul, encode_hangul
from text_control_guard import reject_new_ascii_tilde
from nontext_protection import reject_nontext_overlap, protected_ranges


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline_iso', type=Path)
    parser.add_argument('source_iso', type=Path)
    parser.add_argument('source_elf', type=Path)
    parser.add_argument('plan', type=Path)
    parser.add_argument('output_iso', type=Path)
    parser.add_argument('--baseline-sha256', required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    manifest_path = args.output_iso.with_suffix('.manifest.json')
    if args.output_iso.exists() or manifest_path.exists():
        parser.error('Use fresh output names')
    with args.source_iso.open('rb') as handle:
        assert hashlib.file_digest(handle, 'sha256').hexdigest() == args.source_sha256
    plan = json.loads(args.plan.read_bytes())
    source = args.source_elf.read_bytes()
    assert sha(source) == plan['source_elf_sha256'] and plan['static_verdict'] == 'PASS'
    with iso9660.Iso.from_path(args.baseline_iso) as iso:
        member = iso.find('/PSP_GAME/SYSDIR/EBOOT.BIN')
        offset, size = member.offset, member.size
        baseline = bytes(iso.blob[offset:offset + size])
        font = iso.find('/PSP_GAME/SYSDIR/UPDATE/DATA.BIN')
        font_sha = sha(iso.blob[font.offset:font.offset + font.size])
        geometry = [(x.path, x.lba, x.size) for x in iso.walk()]
    assert sha(baseline) == plan['baseline_elf_sha256'] and font_sha == plan['font_sha256']
    section = ELFFile(io.BytesIO(baseline)).get_section_by_name('.data')
    start, end = section['sh_offset'], section['sh_offset'] + section['sh_size']
    patched = bytearray(baseline)
    ranges, readback = [], []
    for row in sorted(plan['records'], key=lambda r: r['offset']):
        off, limit = row['offset'], row['offset'] + row['capacity'] + 1
        assert start <= off < limit <= end
        assert not any(lo < limit and off < hi for lo, hi in ranges)
        before, after = bytes.fromhex(row['expected_before_hex']), bytes.fromhex(row['replacement_hex'])
        assert len(before) == len(after) == limit - off and baseline[off:limit] == before
        numeric_restore = row.get('kind') in {'restore_original_float32', 'restore_original_nontext_data'}
        if numeric_restore:
            if row['kind'] == 'restore_original_float32':
                assert off % 4 == 0 and limit-off == 4 and row['typed_consumer_verified'] is True
            else:
                assert row['classification_verified'] is True
                assert (off, limit) in protected_ranges()
            assert sha(source[off:limit]) == row['source_raw_sha256']
            assert after == source[off:limit]
        else:
            reject_nontext_overlap(off, limit-off, row['slot_id'])
            nul = source.find(b'\0', off, limit)
            assert nul > off and (nul + 4) & ~3 == limit and not any(source[nul:limit])
            assert sha(source[off:nul]) == row['source_raw_sha256']
            reject_new_ascii_tilde(source[off:nul].decode('cp932'), row['target_ko'], row['slot_id'])
            assert row['existing_font_codes_verified'] is True
            assert after == encode_hangul(row['target_ko']) + bytes(limit-off-len(encode_hangul(row['target_ko'])))
        patched[off:limit] = after
        if not numeric_restore:
            assert decode_hangul(bytes(patched[off:limit]).split(b'\0', 1)[0]) == row['target_ko']
        ranges.append((off, limit))
        readback.append({'slot_id': row['slot_id'], 'offset': off, 'kind': row.get('kind', 'text'),
                        **({'source_exact': True} if numeric_restore else {'target_ko': row['target_ko']})})
    assert ranges
    # A source-bound text repair may also restore corrupted pointer words.
    # Check pointers after every declared write, and permit only explicit
    # source-exact pointer restores to account for an altered baseline word.
    pointer_restores = {r['offset'] for r in plan['records']
                        if r.get('classification') == 'source_text_pointer32'
                        and r.get('kind') == 'restore_original_nontext_data'
                        and r['capacity'] == 3}
    for row in plan['records']:
        for ref in row['pointer_refs']:
            assert patched[ref:ref+4] == source[ref:ref+4]
            assert baseline[ref:ref+4] == source[ref:ref+4] or ref in pointer_restores
    cursor = 0
    for lo, hi in ranges:
        assert patched[cursor:lo] == baseline[cursor:lo]
        cursor = hi
    assert patched[cursor:] == baseline[cursor:]
    assert len(patched) == size
    assert ELFFile(io.BytesIO(patched)).get_section_by_name('.text').data() == ELFFile(io.BytesIO(baseline)).get_section_by_name('.text').data()
    args.output_iso.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.baseline_iso, args.output_iso)
    with args.output_iso.open('r+b') as output:
        for lo, hi in ranges:
            output.seek(offset + lo)
            assert output.write(patched[lo:hi]) == hi-lo
    expected_ranges = [(offset+lo, offset+hi) for lo, hi in ranges]
    original_hash, result_hash = hashlib.sha256(), hashlib.sha256()
    changed, crc, pos = 0, 0, 0
    with args.baseline_iso.open('rb') as before_file, args.output_iso.open('rb') as after_file:
        while before := before_file.read(8 * 1024 * 1024):
            after = after_file.read(len(before))
            assert len(after) == len(before)
            original_hash.update(before); result_hash.update(after); crc = zlib.crc32(after, crc)
            cursor = 0
            for lo, hi in expected_ranges:
                a, b = max(0, lo-pos), min(len(before), hi-pos)
                if a >= b:
                    continue
                assert before[cursor:a] == after[cursor:a]
                changed += sum(x != y for x, y in zip(before[a:b], after[a:b]))
                cursor = b
            assert before[cursor:] == after[cursor:]
            pos += len(before)
        assert not after_file.read(1)
    assert original_hash.hexdigest() == args.baseline_sha256
    assert changed == sum(x != y for x, y in zip(baseline, patched))
    with iso9660.Iso.from_path(args.output_iso) as iso:
        assert [(x.path, x.lba, x.size) for x in iso.walk()] == geometry
        assert bytes(iso.blob[offset:offset+size]) == patched
        font = iso.find('/PSP_GAME/SYSDIR/UPDATE/DATA.BIN')
        assert sha(iso.blob[font.offset:font.offset+font.size]) == font_sha
    report = {'candidate_iso': str(args.output_iso.resolve()), 'candidate_revision': args.revision,
              'iso_sha256': result_hash.hexdigest(), 'iso_crc32': f'{crc:08X}', 'iso_bytes': pos,
              'baseline_iso_sha256': args.baseline_sha256, 'source_iso_sha256': args.source_sha256,
              'elf_sha256': sha(patched), 'font_sha256': font_sha, 'data_slot_count': len(ranges),
              'changed_disc_bytes': changed, 'all_bytes_outside_declared_slots_identical': True,
              'code_preserved': True, 'font_bytes_preserved': True, 'iso_geometry_preserved': True,
              'readback': readback, 'static_verdict': 'PASS', 'runtime_verdict': 'NOT_TESTED',
              'mission_freeze_resolution': 'UNCONFIRMED', 'development_only': True, 'distributed': False}
    manifest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()

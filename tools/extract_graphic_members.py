#!/usr/bin/env python3
"""Extract source-verified graphical AFS members without changing the disc."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from hanpatch.platforms.psp import iso9660


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('iso', type=Path)
    p.add_argument('inventory', type=Path)
    p.add_argument('outdir', type=Path)
    p.add_argument('--expected-iso-sha256', required=True)
    p.add_argument('--include-pattern', action='append', required=True)
    a = p.parse_args()
    with a.iso.open('rb') as f:
        actual = hashlib.file_digest(f, 'sha256').hexdigest()
    assert actual == a.expected_iso_sha256, 'ISO source hash mismatch'
    inventory = json.loads(a.inventory.read_bytes())
    source = inventory.get('members', inventory.get('records', []))
    patterns = [re.compile(x) for x in a.include_pattern]
    selected = [r for r in source if any(x.fullmatch(r['name']) for x in patterns)]
    assert selected and len({r['name'] for r in selected}) == len(selected)
    records = []
    with iso9660.Iso.from_path(a.iso) as iso:
        entry = next(e for e in iso.walk() if e.path == '/PSP_GAME/USRDIR/Z_DATA.BIN')
        base = entry.offset
        assert iso.blob[base:base+4] == b'AFS\0'
        count = struct.unpack_from('<I', iso.blob, base+4)[0]
        directory_offset, directory_size = struct.unpack_from('<II', iso.blob, base+8+count*8)
        assert directory_size == count*48
        for r in selected:
            offset, size = struct.unpack_from('<II', iso.blob, base+8+r['index']*8)
            start = base+directory_offset+r['index']*48
            name = iso.blob[start:start+32].split(b'\0')[0].decode('cp932')
            assert (offset, size, name) == (r['archive_offset'], r['size'], r['name'])
            data = iso.blob[base+offset:base+offset+size]
            assert hashlib.sha256(data).hexdigest() == r['sha256']
            target = a.outdir/'original_pzz'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                assert target.read_bytes() == data, 'Existing extraction differs'
            else:
                target.write_bytes(data)
            records.append(dict(r, iso_member=entry.path,
                iso_absolute_offset=base+offset, local_path=str(target.resolve())))
    out = a.outdir/'extraction_manifest.json'
    data = (json.dumps({'records': records, 'source_iso_sha256': actual}, indent=2)+'\n').encode()
    if out.exists():
        assert out.read_bytes() == data, 'Use another output directory for a different population'
    else:
        out.write_bytes(data)
    print(json.dumps({'source_verified_members': len(records), 'manifest': str(out.resolve())}))


if __name__ == '__main__':
    main()

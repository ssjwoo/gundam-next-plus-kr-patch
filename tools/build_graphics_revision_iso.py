#!/usr/bin/env python3
"""Replace verified fixed-size AFS/PZZ extents in a fresh development ISO.

The member table, directory, file geometry and every unrelated byte are retained.
This does not relocate resources, infer offsets or execute the game.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zlib

from hanpatch.platforms.psp import iso9660
from repack_pzz import parse
from unpack_pzz import detect_xor_key, xor_words
from pzz_integrity import verify_trailer

CHUNK = 8 * 1024 * 1024


def file_sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('baseline_iso',type=Path)
    p.add_argument('source_manifest',type=Path)
    p.add_argument('replacements',type=Path)
    p.add_argument('output_iso',type=Path)
    p.add_argument('--expected-baseline-sha256',required=True)
    a=p.parse_args()
    manifest_out=a.output_iso.with_suffix('.manifest.json')
    if a.output_iso.exists() or manifest_out.exists():
        p.error('Use a fresh candidate filename')
    assert file_sha(a.baseline_iso)==a.expected_baseline_sha256
    sources={r['name']:r for r in json.loads(a.source_manifest.read_bytes())['records']}
    supplied=list(a.replacements.glob('*.pzz'))
    assert supplied and all(x.name in sources for x in supplied)
    writes=[]
    with iso9660.Iso.from_path(a.baseline_iso) as iso:
        geometry=[(r.path,r.lba,r.size) for r in iso.walk()]
        files={r.path:r for r in iso.walk() if not r.is_dir}
        for replacement in supplied:
            s=sources[replacement.name]
            entry=files[s['iso_member']]
            archive=iso.blob[entry.offset:entry.offset+entry.size]
            assert archive[:4]==b'AFS\x00'
            count=struct.unpack_from('<I',archive,4)[0]
            assert s['index']<count
            off,size=struct.unpack_from('<II',archive,8+s['index']*8)
            directory,ds=struct.unpack_from('<II',archive,8+count*8)
            assert ds==count*48
            name=archive[directory+s['index']*48:directory+s['index']*48+32].split(b'\x00')[0].decode('cp932')
            assert (off,size,name)==(s['archive_offset'],s['size'],s['name'])
            old=archive[off:off+size]
            assert hashlib.sha256(old).hexdigest()==s['sha256']
            new=replacement.read_bytes()
            assert len(new)==size and new!=old
            old_key,new_key=detect_xor_key(old),detect_xor_key(new)
            assert old_key==new_key
            od,nd=xor_words(old,old_key),xor_words(new,new_key)
            op,oe=parse(od)
            np,ne=parse(nd)
            assert len(op)==len(np) and oe==ne
            assert od[:0x800]==nd[:0x800]
            assert oe==ne==len(old)-16
            assert verify_trailer(old,od),'Source PZZ loader checksum failed'
            assert verify_trailer(new,nd),'Replacement PZZ loader checksum failed'
            for x,y in zip(op,np):
                assert (x['offset'],x['end'],x['storage'])==(y['offset'],y['end'],y['storage'])
            absolute=entry.offset+off
            assert absolute==s['iso_absolute_offset']
            assert not any(lo<absolute+size and absolute<lo+len(data) for lo,data,_ in writes)
            writes.append((absolute,new,{'name':name,'archive':entry.path,'index':s['index'],
                'absolute_offset':absolute,'bytes':size,'old_sha256':s['sha256'],
                'new_sha256':hashlib.sha256(new).hexdigest(),'part_count':len(np)}))
    a.output_iso.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(a.baseline_iso,a.output_iso)
    with a.output_iso.open('r+b') as f:
        for off,data,_ in writes:
            f.seek(off)
            f.write(data)
    ranges=sorted((off,off+len(data)) for off,data,_ in writes)
    changed=0
    with a.baseline_iso.open('rb') as f0,a.output_iso.open('rb') as f1:
        at=0
        while before:=f0.read(CHUNK):
            after=f1.read(len(before))
            assert len(after)==len(before)
            if before!=after:
                # Compare protected gaps directly. Counting differences only in
                # verified extents avoids scanning every extent for every byte.
                cursor=0
                for lo,hi in ranges:
                    start=max(0,lo-at)
                    end=min(len(before),hi-at)
                    if start>=end:
                        continue
                    assert before[cursor:start]==after[cursor:start],'Unexpected disc change'
                    changed+=sum(x!=y for x,y in zip(before[start:end],after[start:end]))
                    cursor=end
                assert before[cursor:]==after[cursor:],'Unexpected disc change'
            at+=len(before)
        assert not f1.read(1)
    with iso9660.Iso.from_path(a.output_iso) as iso:
        assert [(r.path,r.lba,r.size) for r in iso.walk()]==geometry
        for off,data,_ in writes:
            assert iso.blob[off:off+len(data)]==data
    crc=0
    with a.output_iso.open('rb') as f:
        while data:=f.read(CHUNK):
            crc=zlib.crc32(data,crc)
    result={'candidate_iso':str(a.output_iso.resolve()),'baseline_iso_sha256':a.expected_baseline_sha256,
        'iso_sha256':file_sha(a.output_iso),'iso_crc32':f'{crc&0xffffffff:08X}',
        'iso_bytes':a.output_iso.stat().st_size,'members':[r for _,_,r in writes],
        'changed_disc_bytes':changed,'iso_member_geometry_preserved':True,
        'unaffected_iso_bytes_preserved':True,'afs_tables_and_pzz_geometry_preserved':True,
        'pzz_loader_checksums_verified':True,
        'static_verdict':'PASS','runtime_verdict':'NOT_TESTED','development_only':True,
        'whole_game_text_complete':False,'graphics_localization_complete':False}
    manifest_out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()

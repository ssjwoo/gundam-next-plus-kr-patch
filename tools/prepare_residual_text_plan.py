#!/usr/bin/env python3
"""Compile an offset/hash-bound Korean catalog into fixed ELF .data writes.

Inputs are local user-owned game files. No font, pointer, executable code or
resource allocation is changed. The resulting byte plan must remain private.
"""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from audit_workbook_font import font_records
from make_hangul_poc import encode_hangul, decode_hangul
from text_control_guard import reject_new_ascii_tilde
from nontext_protection import reject_nontext_overlap


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source_elf',type=Path)
    p.add_argument('baseline_elf',type=Path)
    p.add_argument('baseline_font',type=Path)
    p.add_argument('catalog',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    if a.output.exists():
        p.error('Use a fresh private output filename')
    source=a.source_elf.read_bytes(); baseline=a.baseline_elf.read_bytes()
    catalog=json.loads(a.catalog.read_bytes()); glyphs,font_meta=font_records(a.baseline_font)
    assert sha(source)==catalog['source_elf_sha256']
    assert sha(baseline)==catalog['baseline_elf_sha256']
    assert font_meta['sha256']==catalog['font_sha256']
    src_section=ELFFile(BytesIO(source)).get_section_by_name('.data')
    section=ELFFile(BytesIO(baseline)).get_section_by_name('.data')
    assert section and src_section
    start,end=section['sh_offset'],section['sh_offset']+section['sh_size']
    assert (section['sh_offset'],section['sh_addr'])==(src_section['sh_offset'],src_section['sh_addr'])
    rows=[]; occupied=[]
    for r in catalog['rows']:
        off=r['offset']; limit=off+r['capacity']+1
        reject_nontext_overlap(off, limit-off, r['slot_id'])
        assert r['slot_id']==f'SOURCE_{off:08X}' and start<=off<limit<=end
        nul=source.find(b'\0',off,limit)
        assert nul>off and (nul+4)&~3==limit
        assert not any(source[nul:limit])
        assert sha(source[off:nul])==r['source_raw_sha256']
        reject_new_ascii_tilde(source[off:nul].decode('cp932'), r['target_ko'], r['slot_id'])
        if 'baseline_slot_sha256' in r:
            assert sha(baseline[off:limit])==r['baseline_slot_sha256']
        if 'before_ko' in r:
            assert decode_hangul(baseline[off:limit].split(b'\0',1)[0])==r['before_ko']
        assert not any(lo<limit and off<hi for lo,hi in occupied)
        occupied.append((off,limit))
        address=section['sh_addr']+off-start
        refs=[int(x.strip(),0) for x in r['pointer_refs_hex'].split(',') if x.strip()]
        for ref in refs:
            assert source[ref:ref+4]==baseline[ref:ref+4]==struct.pack('<I',address)
        encoded=encode_hangul(r['target_ko'])
        assert len(encoded)<=r['capacity'] and decode_hangul(encoded)==r['target_ko']
        i=0; codes=[]
        while i<len(encoded):
            lead=encoded[i]
            if lead<128:
                if lead>=32: codes.append(lead)
                i+=1
            else:
                codes.append(256+(lead-128)*128+encoded[i+1]-128); i+=2
        assert not set(codes)-glyphs.keys(),('Missing existing font codes',r['slot_id'])
        replacement=encoded+b'\0'*(limit-off-len(encoded))
        assert replacement!=baseline[off:limit]
        rows.append(dict(r,expected_before_hex=baseline[off:limit].hex(),
                         replacement_hex=replacement.hex(),pointer_refs=refs,
                         existing_font_codes_verified=True))
    plan={'baseline_elf_sha256':sha(baseline),'source_elf_sha256':sha(source),
          'font_sha256':font_meta['sha256'],'font_and_ctype_022_preserved':True,
          'records':rows,'static_verdict':'PASS','runtime_verdict':'NOT_TESTED'}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'slots':len(rows),'existing_font_codes':'PASS',
                      'source_offset_and_hash_bindings':'PASS','output':str(a.output)}))


if __name__=='__main__':
    main()

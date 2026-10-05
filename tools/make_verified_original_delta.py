#!/usr/bin/env python3
"""Encode a local delta and verify its complete decoded hash without a second ISO."""
import argparse,hashlib,json,subprocess,zlib
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('source_iso',type=Path);p.add_argument('candidate_manifest',type=Path)
 p.add_argument('xdelta_exe',type=Path);p.add_argument('output_delta',type=Path)
 p.add_argument('--source-sha256',required=True);p.add_argument('--revision',required=True)
 a=p.parse_args();report_path=a.output_delta.parent/f'xdelta_roundtrip_{a.revision}.json'
 if a.output_delta.exists() or report_path.exists():p.error('Use fresh output filenames')
 manifest=json.loads(a.candidate_manifest.read_bytes());candidate=Path(manifest['candidate_iso'])
 assert manifest['static_verdict']=='PASS' and candidate.stat().st_size==manifest['iso_bytes']
 with a.source_iso.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==a.source_sha256
 print('Encoding original-based '+a.revision+' delta',flush=True)
 subprocess.run([str(a.xdelta_exe),'-e','-s',str(a.source_iso),str(candidate),str(a.output_delta)],check=True)
 print('Decoding '+a.revision+' to a hash stream',flush=True)
 proc=subprocess.Popen([str(a.xdelta_exe),'-d','-c','-s',str(a.source_iso),str(a.output_delta)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 digest=hashlib.sha256();n=0;crc=0
 while chunk:=proc.stdout.read(8*1024*1024):digest.update(chunk);n+=len(chunk);crc=zlib.crc32(chunk,crc)
 err=proc.stderr.read().decode(errors='replace');assert proc.wait()==0,err
 assert digest.hexdigest()==manifest['iso_sha256'] and n==manifest['iso_bytes'] and f'{crc:08X}'==manifest['iso_crc32']
 blob=a.output_delta.read_bytes()
 report={'revision':a.revision,'original_iso_sha256':a.source_sha256,'candidate_iso_sha256':manifest['iso_sha256'],
  'xdelta_sha256':hashlib.sha256(blob).hexdigest(),'xdelta_crc32':f'{zlib.crc32(blob):08X}','xdelta_bytes':len(blob),
  'roundtrip_sha256':digest.hexdigest(),'roundtrip_bytes':n,'roundtrip_method':'Decoded stdout streamed into SHA256 and CRC32; no duplicate ISO',
  'verdict':'PASS','runtime_verdict':'NOT_TESTED','mission_freeze_resolution':'UNCONFIRMED'}
 report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report),flush=True)

if __name__=='__main__':main()

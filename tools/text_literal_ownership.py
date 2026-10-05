"""Require one complete owner for the confirmed scanner-fragment literals."""
from functools import lru_cache
import json
from pathlib import Path
POLICY=Path(__file__).resolve().parents[1]/'translations/full_dialogue_literals_ko_2026-10-05.json'
@lru_cache(maxsize=1)
def complete_literal_ranges():
 policy=json.loads(POLICY.read_bytes())
 assert policy['source_elf_sha256']=='ce917a0f7289ccce3a0db8f0783529f93ff31789c0ee0bb1842ce632f0dd0c06'
 return [(r['offset'],r['offset']+r['capacity']+1) for r in policy['rows']]
def reject_partial_literal(offset,span,slot='text',ranges=None):
 for lo,hi in complete_literal_ranges() if ranges is None else ranges:
  if lo<offset+span and offset<hi and (offset,offset+span)!=(lo,hi):
   raise ValueError(f'{slot}: write must own the complete source literal at 0x{lo:08X}')

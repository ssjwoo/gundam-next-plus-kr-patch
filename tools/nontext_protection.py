"""Protect source-proven non-text regions from all text-slot writers."""
from functools import lru_cache
import json
from pathlib import Path
from text_literal_ownership import reject_partial_literal

POLICY = Path(__file__).resolve().parents[1] / 'translations/nontext_protected_fields_2026-10-05.json'


@lru_cache(maxsize=1)
def protected_ranges():
    policy = json.loads(POLICY.read_bytes())
    assert policy['source_elf_sha256'] == 'ce917a0f7289ccce3a0db8f0783529f93ff31789c0ee0bb1842ce632f0dd0c06'
    return ([(r['offset'], r['offset'] + r['capacity'] + 1) for r in policy['records']]
            + [(r['offset'], r['offset'] + r['bytes']) for r in policy.get('protected_containers', [])]
            + [(r['offset'], r['offset'] + 4) for r in policy.get('protected_pointer_words', [])])


def reject_nontext_overlap(offset, span, slot='text', ranges=None):
    for lo, hi in protected_ranges() if ranges is None else ranges:
        if lo < offset + span and offset < hi:
            raise ValueError(f'{slot}: text write overlaps a source-proven non-text region at 0x{lo:08X}')
    if ranges is None:
        reject_partial_literal(offset,span,slot)

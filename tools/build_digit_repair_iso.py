#!/usr/bin/env python3
"""Build a separate ISO and prove the audited digit repair changes 37 bytes.

The input is the supplied Korean patch ISO, not the Japanese original. This
tool never launches an emulator or overwrites an existing output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from hanpatch.platforms.psp import iso9660


PROVIDED_ISO_SHA256 = "c0e2ac8154cf240649229a95bcf2a52f37688096ae2918e16c7857c1491a4992"
CHUNK_BYTES = 8 * 1024 * 1024


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("provided_iso", type=Path)
    parser.add_argument("repair_dir", type=Path, help="Output directory of repair_fixed_width_digits.py")
    parser.add_argument("output_iso", type=Path)
    args = parser.parse_args()
    source, target = args.provided_iso, args.output_iso
    manifest_path = target.with_suffix(".manifest.json")
    if target.exists() or manifest_path.exists():
        parser.error("Output ISO or manifest already exists")
    if file_sha256(source) != PROVIDED_ISO_SHA256:
        parser.error("Source ISO differs from the audited provided patch")
    report = json.loads((args.repair_dir / "repair_report.json").read_text(encoding="utf-8"))
    files = {
        "/PSP_GAME/SYSDIR/EBOOT.BIN": (args.repair_dir / "digit_fixed.elf").read_bytes(),
        "/PSP_GAME/SYSDIR/UPDATE/DATA.BIN": (args.repair_dir / "digit_fixed.pgf").read_bytes(),
    }
    expected_hashes = {
        "/PSP_GAME/SYSDIR/EBOOT.BIN": "077e99a31d470b7b2234312197b0d3537b4e9a6e6af55efc497e9ebba3090781",
        "/PSP_GAME/SYSDIR/UPDATE/DATA.BIN": "4e75a6cb3d797faa8ea86f80645620c61c5b64e8673c672f041ab7b624ae86ec",
    }
    if (report["output_elf_sha256"] != expected_hashes["/PSP_GAME/SYSDIR/EBOOT.BIN"]
            or report["output_font_sha256"] != expected_hashes["/PSP_GAME/SYSDIR/UPDATE/DATA.BIN"]):
        parser.error("Repair report does not describe the audited output files")
    expected_changes = report["elf_changed_bytes"] + report["font_changed_bytes"]
    if expected_changes != 37 or report["static_verdict"] != "PASS":
        parser.error("Repair report differs from the verified 37-byte repair")
    ranges = []
    with iso9660.Iso.from_path(source) as image:
        entries = {entry.path: entry for entry in image.walk() if not entry.is_dir}
        for name, data in files.items():
            entry = entries[name]
            if len(data) != entry.size or hashlib.sha256(data).hexdigest() != expected_hashes[name]:
                parser.error("Replacement identity or size changed")
            ranges.append((entry.offset, entry.offset + entry.size))
    target.parent.mkdir(parents=True, exist_ok=True)
    iso9660.write(source, target, files)
    if target.stat().st_size != source.stat().st_size:
        raise AssertionError("ISO size changed")
    changed = []
    with source.open("rb") as left, target.open("rb") as right:
        offset = 0
        while before := left.read(CHUNK_BYTES):
            after = right.read(len(before))
            if before != after:
                for index, (a, b) in enumerate(zip(before, after)):
                    if a != b:
                        address = offset + index
                        if not any(start <= address < end for start, end in ranges):
                            raise AssertionError(f"Unexpected disc byte change at {address:#x}")
                        changed.append(address)
            offset += len(before)
    if len(changed) != expected_changes:
        raise AssertionError("Unexpected change count")
    with iso9660.Iso.from_path(target) as image:
        entries = {entry.path: entry for entry in image.walk() if not entry.is_dir}
        for name, data in files.items():
            entry = entries[name]
            if bytes(image.blob[entry.offset:entry.offset + entry.size]) != data:
                raise AssertionError("Embedded file readback differs")
    manifest = {
        "source_iso": str(source.resolve()), "source_iso_sha256": PROVIDED_ISO_SHA256,
        "candidate_iso": str(target.resolve()), "candidate_sha256": file_sha256(target),
        "size_bytes": target.stat().st_size, "changed_disc_bytes": len(changed),
        "changed_disc_offsets_hex": [hex(address) for address in changed],
        "iso_metadata_and_all_other_bytes_unchanged": True,
        "embedded_files_readback": expected_hashes,
        "static_verdict": "PASS", "runtime_verdict": "NOT_TESTED",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in manifest.items() if key != "changed_disc_offsets_hex"}, indent=2))


if __name__ == "__main__":
    main()

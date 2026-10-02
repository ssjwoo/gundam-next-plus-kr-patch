"""Regression checks for the game's source-used CP932 symbol pairs."""

from __future__ import annotations

import unittest
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from make_hangul_poc import (
    DISPLACED_HANGUL,
    RESERVED_HANGUL_CODEPOINTS,
    RUNTIME_INDEX_GLYPHS,
    decode_hangul,
    encode_hangul,
)


class HangulSymbolCollisionTests(unittest.TestCase):
    def test_source_used_pairs_are_reserved(self) -> None:
        expected = {
            0xAC99: (0x81, 0x99),
            0xAC9A: (0x81, 0x9A),
            0xACA5: (0x81, 0xA5),
        }
        self.assertEqual(set(RESERVED_HANGUL_CODEPOINTS), set(expected))
        for codepoint, pair in expected.items():
            with self.subTest(codepoint=f"U+{codepoint:04X}", pair=pair):
                index = codepoint - 0xAC00
                self.assertEqual((0x80 + (index >> 7), 0x80 + (index & 0x7F)), pair)
                with self.assertRaisesRegex(ValueError, f"U\\+{codepoint:04X}"):
                    encode_hangul(chr(codepoint))

    def test_remaining_hangul_round_trip(self) -> None:
        rejected = set(RESERVED_HANGUL_CODEPOINTS) | {
            0xAC00 + index for index in RUNTIME_INDEX_GLYPHS
            if 0xAC00 + index not in DISPLACED_HANGUL
        }
        encoded_pairs = set()
        for codepoint in range(0xAC00, 0xD7A4):
            if codepoint in rejected:
                with self.assertRaises(ValueError):
                    encode_hangul(chr(codepoint))
                continue
            encoded = encode_hangul(chr(codepoint))
            self.assertEqual(decode_hangul(encoded), chr(codepoint))
            self.assertEqual(len(encoded), 2)
            self.assertLess(encoded[0], 0xF0)
            self.assertGreaterEqual(encoded[1], 0x80)
            self.assertNotIn(encoded, encoded_pairs)
            encoded_pairs.add(encoded)
        self.assertEqual(len(encoded_pairs), 0xD7A4 - 0xAC00 - len(rejected))

    def test_displaced_syllable_readback_in_builders(self) -> None:
        from apply_workbook_slots import decode_hangul as slot_decode
        from build_korean_eboot import decode_hangul as build_decode

        # Fixed v19 mapping: U+CC22 moves from the trademark slot to index 12000.
        self.assertEqual(encode_hangul("찢"), b"\xDD\xE0")
        for decoder in (decode_hangul, slot_decode, build_decode):
            with self.subTest(decoder=decoder):
                self.assertEqual(decoder(b"\xDD\xE0"), "찢")

    def test_ascii_and_mixed_text_round_trip(self) -> None:
        for text in ("", "".join(map(chr, range(0x80))), "MS 10기\n찢어진 장갑"):
            with self.subTest(text=text):
                self.assertEqual(decode_hangul(encode_hangul(text)), text)

    def test_malformed_pairs_are_rejected(self) -> None:
        for raw in (b"\x80", b"A\x80", b"\x80\x7F", b"\xF0\x80", b"\xEF\xFF"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                decode_hangul(raw)

    def test_reserved_pairs_are_rejected(self) -> None:
        indices = set(RUNTIME_INDEX_GLYPHS) | {
            codepoint - 0xAC00 for codepoint in RESERVED_HANGUL_CODEPOINTS
        }
        for index in indices:
            raw = bytes((0x80 + (index >> 7), 0x80 + (index & 0x7F)))
            with self.subTest(index=index), self.assertRaises(ValueError):
                decode_hangul(raw)

    def test_workbook_slot_write_with_displaced_syllable(self) -> None:
        # Synthetic slot fixture; no copyrighted game data or executable needed.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.elf"
            output = root / "output.elf"
            workbook = root / "workbook.csv"
            report = root / "report.json"
            prefix = b"unchanged prefix"
            suffix = b"unchanged suffix"
            capacity = 12
            original_slot = "引き裂く".encode("cp932").ljust(capacity + 1, b"\0")
            original = prefix + original_slot + suffix
            source.write_bytes(original)
            with workbook.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "id", "status", "source_jp", "target_ko", "file_offset_hex", "capacity_bytes"
                ])
                writer.writeheader()
                writer.writerow({
                    "id": "fixture", "status": "translated", "source_jp": "引き裂く",
                    "target_ko": "찢", "file_offset_hex": hex(len(prefix)), "capacity_bytes": capacity,
                })
            script = Path(__file__).with_name("apply_workbook_slots.py")
            command = [sys.executable, str(script), str(source), str(workbook),
                       "--output-elf", str(output), "--report", str(report)]
            result = subprocess.run(command, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(output.read_bytes(), prefix + b"\xDD\xE0" + bytes(capacity - 1) + suffix)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["counts"]["applied"], 1)

            # Reapplying the same translation is a no-op, including the moved index.
            command[2] = str(output)
            result = subprocess.run(command, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["counts"]["already_applied"], 1)
            self.assertEqual(output.read_bytes(), prefix + b"\xDD\xE0" + bytes(capacity - 1) + suffix)


if __name__ == "__main__":
    unittest.main()

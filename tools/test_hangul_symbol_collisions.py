"""Regression checks for the game's source-used CP932 symbol pairs."""

from __future__ import annotations

import unittest

from make_hangul_poc import RESERVED_HANGUL_CODEPOINTS, encode_hangul


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
        accepted = 0
        for codepoint in range(0xAC00, 0xD7A4):
            if codepoint in RESERVED_HANGUL_CODEPOINTS:
                continue
            lead, trail = encode_hangul(chr(codepoint))
            decoded = 0xAC00 + ((lead - 0x80) << 7) + (trail - 0x80)
            self.assertEqual(decoded, codepoint)
            self.assertLess(lead, 0xF0)
            accepted += 1
        self.assertEqual(accepted, 11169)


if __name__ == "__main__":
    unittest.main()

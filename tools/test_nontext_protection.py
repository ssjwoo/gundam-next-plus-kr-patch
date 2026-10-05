import unittest
from nontext_protection import reject_nontext_overlap, protected_ranges


class NumericProtectionTests(unittest.TestCase):
    def test_actual_previously_misclassified_slots_are_blocked(self):
        for lo, hi in protected_ranges():
            with self.assertRaises(ValueError):
                reject_nontext_overlap(lo, hi-lo+1)

    def test_partial_writer_cannot_enter_field(self):
        with self.assertRaises(ValueError):
            reject_nontext_overlap(96, 8, ranges=[(100, 104)])

    def test_adjacent_text_does_not_overlap(self):
        reject_nontext_overlap(96, 4, ranges=[(100, 104)])
        reject_nontext_overlap(104, 8, ranges=[(100, 104)])

    def test_large_writer_cannot_cover_field(self):
        with self.assertRaises(ValueError):
            reject_nontext_overlap(80, 40, ranges=[(100, 104)])


if __name__ == '__main__':
    unittest.main()

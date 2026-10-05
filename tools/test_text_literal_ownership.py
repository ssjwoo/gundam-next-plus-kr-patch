import unittest
from text_literal_ownership import complete_literal_ranges,reject_partial_literal
class LiteralOwnershipTests(unittest.TestCase):
 def test_full_actual_owners_pass(self):
  for lo,hi in complete_literal_ranges():reject_partial_literal(lo,hi-lo)
 def test_actual_suffix_start_is_rejected(self):
  for lo,hi in complete_literal_ranges():
   with self.assertRaises(ValueError):reject_partial_literal(lo+1,hi-lo-1)
 def test_adjacent_write_passes(self):
  reject_partial_literal(96,4,ranges=[(100,112)])
  reject_partial_literal(112,4,ranges=[(100,112)])
 def test_large_alias_cannot_cover_literal(self):
  with self.assertRaises(ValueError):reject_partial_literal(96,20,ranges=[(100,112)])
if __name__=='__main__':unittest.main()

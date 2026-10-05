import unittest

from text_control_guard import reject_new_ascii_tilde


class TextControlGuardTests(unittest.TestCase):
    def test_fullwidth_wave_does_not_authorize_ascii_command(self):
        with self.assertRaisesRegex(ValueError, "introduced ASCII"):
            reject_new_ascii_tilde("失敗できないよぉ～！", "실패하면 안 돼~!")

    def test_bare_tilde_before_two_punctuation_marks_also_rejected(self):
        with self.assertRaises(ValueError):
            reject_new_ascii_tilde("へっへっへ～！！", "헤헤헤~!!")

    def test_individually_corrected_punctuation_is_accepted(self):
        reject_new_ascii_tilde("ばかにするな～！", "얕보지 마!")

    def test_source_color_and_font_commands_are_accepted(self):
        reject_new_ascii_tilde("~f0名前~f2", "~f0이름~f2")
        reject_new_ascii_tilde("~pS名前~pE", "~pS이름~pE")

    def test_installer_source_controls_remain_accepted(self):
        reject_new_ascii_tilde("進行~10~3", "진행~10~3")

    def test_existing_commands_do_not_authorize_extra_punctuation(self):
        with self.assertRaises(ValueError):
            reject_new_ascii_tilde("~f0名前~f2", "~f0이름~f2~!")

    def test_removing_an_invalid_baseline_command_is_permitted(self):
        reject_new_ascii_tilde("얕보지 마~!", "얕보지 마!")


if __name__ == "__main__":
    unittest.main()

import unittest

import wordle_model


class ModelTests(unittest.TestCase):
    def test_extract_rows_count(self):
        rows = wordle_model.load_rows()
        self.assertEqual(len(rows), 359)
        self.assertEqual(rows[0]["word"], "manly")

    def test_features_eerie(self):
        features = wordle_model.word_features("EERIE")
        self.assertEqual(features["length"], 5)
        self.assertEqual(features["unique"], 3)
        self.assertEqual(features["vowels"], 4)


if __name__ == "__main__":
    unittest.main()

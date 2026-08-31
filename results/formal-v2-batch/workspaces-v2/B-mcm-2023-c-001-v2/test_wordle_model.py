import json
import unittest
from pathlib import Path

import wordle_model as wm


CASE = Path(r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\mcm-2023-c.json")


class WordleModelTests(unittest.TestCase):
    def test_load_records_ignores_padding_and_parses_percentages(self):
        records, audit = wm.load_records(CASE)
        self.assertEqual(len(records), 358)
        self.assertEqual(audit["rows_total"], 481)
        self.assertEqual(records[0]["word"], "slump")
        self.assertLess(abs(sum(records[0]["outcomes"]) - 1.0), 1e-9)

    def test_word_features_are_deterministic(self):
        f = wm.word_features("EERIE")
        self.assertEqual(f["length"], 5)
        self.assertEqual(f["unique_letters"], 3)
        self.assertEqual(f["repeated_letters"], 2)
        self.assertEqual(f["vowels"], 4)

    def test_prediction_interval_and_classification_have_expected_shapes(self):
        records, _ = wm.load_records(CASE)
        forecast = wm.forecast_reported(records)
        self.assertGreater(forecast["point"], 0)
        self.assertLessEqual(forecast["lower"], forecast["point"])
        self.assertLessEqual(forecast["point"], forecast["upper"])
        cls = wm.classify_difficulty(records)
        self.assertLessEqual(0, cls["holdout_accuracy"])
        self.assertLessEqual(cls["holdout_accuracy"], 1)
        self.assertIn(cls["eerie_label"], {"easy", "medium", "hard"})


if __name__ == "__main__":
    unittest.main()

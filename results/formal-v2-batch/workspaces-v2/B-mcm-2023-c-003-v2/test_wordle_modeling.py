import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import wordle_modeling as wm


CASE_PATH = Path(
    "C:/Users/伍辰杰/Documents/ChatGPT/mathmodel/"
    "math-modeling-competition-skills/benchmarks/case-summaries/mcm-2023-c.json"
)


class WordleModelingPublicInterfaceTests(unittest.TestCase):
    def test_load_rows_uses_audited_rows_only(self):
        rows, audit = wm.load_audited_rows(CASE_PATH)
        self.assertEqual(359, len(rows))
        self.assertEqual("2022-01-07", rows[0]["date"].isoformat())
        self.assertEqual("2022-12-31", rows[-1]["date"].isoformat())
        self.assertEqual(359, audit["valid_data_rows"])
        self.assertEqual(481, audit["audited_sheet_rows"])
        self.assertTrue(all(len(row["distribution"]) == 7 for row in rows))

    def test_word_features_capture_repetition_without_external_data(self):
        rows, _ = wm.load_audited_rows(CASE_PATH)
        feature_names, features = wm.build_word_features(
            [row["word"] for row in rows] + ["eerie"]
        )
        eerie = dict(zip(feature_names, features[-1]))
        self.assertEqual(4.0, eerie["vowel_count"])
        self.assertEqual(3.0, eerie["unique_letters"])
        self.assertEqual(2.0, eerie["repeat_excess"])

    def test_compositional_transform_returns_a_simplex(self):
        percentages = np.array([[0, 2, 17, 37, 29, 12, 2]], dtype=float)
        transformed = wm.alr_transform(percentages)
        restored = wm.alr_inverse(transformed)
        self.assertAlmostEqual(100.0, float(restored.sum()), places=9)
        self.assertTrue(np.all(restored >= 0))

    def test_rolling_origin_splits_never_leak_future_rows(self):
        splits = wm.rolling_origin_splits(359, horizon=30, min_train=180)
        self.assertGreaterEqual(len(splits), 3)
        for train, test in splits:
            self.assertLess(int(train.max()), int(test.min()))

    def test_cli_writes_structured_report_and_nine_figures(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            exit_code = wm.main(
                ["--input", str(CASE_PATH), "--output", str(output)]
            )
            self.assertEqual(0, exit_code)
            report = json.loads((output / "modeling_report.json").read_text("utf-8"))
            required = {
                "problem_framing", "data_audit", "assumptions",
                "candidate_models", "baseline", "math_specification",
                "code_prototype", "experiment", "validation",
                "sensitivity_robustness", "falsification",
                "reviewer_risks", "reproducibility_manifest",
            }
            self.assertTrue(required.issubset(report))
            self.assertEqual(60, report["experiment"]["march_1_2023"]["horizon_days"])
            figures = list((output / "figures").glob("*.svg"))
            self.assertEqual(9, len(figures))
            self.assertTrue(all(path.stat().st_size > 500 for path in figures))


if __name__ == "__main__":
    unittest.main()

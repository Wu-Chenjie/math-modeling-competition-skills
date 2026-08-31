import json
import tempfile
import unittest
from pathlib import Path

import model_run


CASE_PATH = Path(
    r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills"
    r"\benchmarks\case-summaries\icm-2023-d.json"
)


class ModelRunContractTests(unittest.TestCase):
    def test_report_preserves_missing_data_as_pending(self):
        case = model_run.load_case(CASE_PATH)
        report = model_run.build_report(case)

        self.assertEqual(report["data_audit"]["official_goals_found"], 17)
        self.assertEqual(report["data_audit"]["data_files_count"], 0)
        self.assertEqual(report["baseline"]["ranking_status"], "pending")
        self.assertTrue(all(item["priority_score"] is None for item in report["baseline"]["goals"]))
        self.assertIn("experiment", report)
        self.assertIn("falsification", report)
        self.assertIn("reviewer_risks", report)

    def test_run_writes_machine_readable_outputs_and_three_audit_figures(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = model_run.run(CASE_PATH, Path(tmp))
            metrics = json.loads((Path(tmp) / "metrics.json").read_text(encoding="utf-8"))

            self.assertEqual(receipt["status"], "partial")
            self.assertEqual(receipt["figures_count"], 3)
            self.assertEqual(metrics["rows_available"], 0)
            self.assertEqual(metrics["priority_ranking_computed"], False)
            self.assertEqual(len(list((Path(tmp) / "figures").glob("*.svg"))), 3)


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import model


CASE = Path(r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\mcm-2023-b.json")


class ModelTests(unittest.TestCase):
    def test_case_summary_is_loaded_without_external_data(self):
        case = model.load_case(CASE)
        self.assertEqual(case["case_id"], "mcm-2023-b")
        self.assertEqual(case["data_files"], [])

    def test_evaluate_policy_is_bounded_and_constraint_respecting(self):
        case = model.load_case(CASE)
        result = model.evaluate_policy(case, {"community": 1, "zoning": 1, "levy": 0}, "baseline")
        self.assertGreaterEqual(result["robust_score"], 0.0)
        self.assertLessEqual(result["robust_score"], 1.0)
        self.assertLessEqual(result["capacity_used"], result["capacity_limit"])
        self.assertEqual(set(result["objectives"]), {"wildlife", "livelihood", "conflict", "cost"})

    def test_cli_writes_machine_readable_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            metrics, figures, report = root / "metrics.json", root / "figures", root / "report.md"
            proc = subprocess.run([sys.executable, "model.py", "--case", str(CASE), "--metrics", str(metrics), "--figures", str(figures), "--report", str(report)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(metrics.read_text(encoding="utf-8"))
            self.assertEqual(payload["case_id"], "mcm-2023-b")
            self.assertGreaterEqual(len(list(figures.glob("*.png"))), 9)
            self.assertTrue(report.exists())

    def test_sensitivity_and_projection_are_computed(self):
        case = model.load_case(CASE)
        policies = list(model.enumerate_policies())
        sensitivity = model.weight_sensitivity(case, policies)
        self.assertEqual(sum(sensitivity["selection_counts"].values()), len(sensitivity["weight_sets"]))
        projection = model.project_long_term(case, policies[0], years=20)
        self.assertEqual(len(projection["baseline"]), 21)
        self.assertTrue(all(0.0 <= value <= 1.0 for values in projection.values() for value in values))

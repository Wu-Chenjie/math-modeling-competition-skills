import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

class ModelRunTests(unittest.TestCase):
    def test_end_to_end_outputs_are_consistent(self):
        with tempfile.TemporaryDirectory() as td:
            proc = subprocess.run(
                [sys.executable, str(ROOT / "run_model.py"), "--output-root", td],
                text=True, capture_output=True, check=True
            )
            receipt = json.loads(proc.stdout)
            metrics = json.loads(Path(receipt["metrics_path"]).read_text(encoding="utf-8"))
            self.assertEqual(receipt["figures_count"], 12)
            self.assertTrue(metrics["tests"]["closure_normalized"])
            self.assertEqual(len(metrics["q3"]), 8)
            self.assertEqual(metrics["input_scope"]["sheet_rows"], {"表单1": 59, "表单2": 70, "表单3": 9})
            self.assertTrue(all(0 <= x["sensitivity_stability"] <= 1 for x in metrics["q3"]))

if __name__ == "__main__":
    unittest.main()


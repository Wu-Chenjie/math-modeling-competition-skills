import tempfile
import unittest
from pathlib import Path

from run_model import build_report, composite_risk, intervention_effect


class ModelTests(unittest.TestCase):
    def test_composite_risk_bounds_and_monotonicity(self):
        low = composite_risk([0, 0, 0, 0, 0, 0, 0])
        high = composite_risk([1, 1, 1, 1, 1, 1, 1])
        more_harm = composite_risk([0.8, 0, 0, 0, 0, 0, 0])
        self.assertTrue(0 <= low <= 1)
        self.assertTrue(0 <= high <= 1)
        self.assertGreater(more_harm, low)


    def test_intervention_reduces_harm_and_preserves_safety_floor(self):
        baseline = [0.8, 0.7, 0.6, 0.5, 0.7, 0.8, 0.6]
        mitigated = intervention_effect(baseline, "adaptive_controls")
        self.assertLess(mitigated[0], baseline[0])
        self.assertLess(mitigated[1], baseline[1])
        self.assertGreaterEqual(mitigated[6], 0.4)


    def test_report_flags_missing_rows_without_scores(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            summary = {"case_id": "x", "data_files": [], "data_audit": []}
            report = build_report(summary, out)
            self.assertEqual(report["data_audit"]["rows_available"], 0)
            self.assertEqual(report["validation"]["empirical_status"], "pending")
            self.assertFalse((out / "results" / "metrics.json").exists())

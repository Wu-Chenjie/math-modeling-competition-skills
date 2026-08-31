import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import analysis


class AnalysisTests(unittest.TestCase):
    def test_close_composition_handles_zeros_and_closes(self):
        closed = analysis.close_composition(np.array([[80.0, 20.0, 0.0]]), 0.01)
        self.assertTrue(np.all(closed > 0))
        self.assertAlmostEqual(float(closed.sum()), 1.0, places=12)

    def test_clr_round_trip(self):
        composition = analysis.close_composition(np.array([[70.0, 20.0, 10.0]]), 0.01)
        restored = analysis.inverse_clr(analysis.clr(composition))
        np.testing.assert_allclose(restored, composition, rtol=1e-10, atol=1e-12)

    def test_validity_rule_is_inclusive(self):
        sums = np.array([84.99, 85.0, 100.0, 105.0, 105.01])
        self.assertEqual(analysis.valid_composition_mask(sums).tolist(), [False, True, True, True, False])

    def test_sampling_label_overrides_surface_weathering(self):
        self.assertEqual(analysis.sample_weathering("49未风化点", "风化"), "无风化")
        self.assertEqual(analysis.sample_weathering("54严重风化点", "无风化"), "风化")
        self.assertEqual(analysis.sample_weathering("03部位1", "无风化"), "无风化")

    def test_artifact_id_extracts_numeric_prefix(self):
        self.assertEqual(analysis.artifact_id("42未风化点2"), "42")
        self.assertEqual(analysis.artifact_id("A8"), "A8")

    def test_run_writes_machine_readable_outputs(self):
        source = Path(analysis.DEFAULT_INPUT)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            receipt = analysis.run(source, output, permutations=9, perturbations=9)
            metrics = json.loads((output / "results" / "metrics.json").read_text(encoding="utf-8"))
            report = json.loads((output / "results" / "modeling_report.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["figures_count"], 12)
            self.assertEqual(metrics["input_audit"]["unknown_rows"], 8)
            self.assertEqual(set(report), set(analysis.REPORT_SECTIONS))


if __name__ == "__main__":
    unittest.main()

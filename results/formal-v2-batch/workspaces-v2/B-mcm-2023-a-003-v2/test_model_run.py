import json
import tempfile
import unittest
from pathlib import Path

import model_run


class ModelBehaviorTests(unittest.TestCase):
    def test_weather_is_deterministic_and_bounded(self):
        scenario = model_run.SCENARIOS[1]
        first = model_run.generate_weather(40, scenario, 17)
        second = model_run.generate_weather(40, scenario, 17)
        self.assertEqual(first, second)
        self.assertTrue(all(0.0 <= value <= 1.0 for value in first))

    def test_state_remains_nonnegative_and_finite(self):
        run = model_run.simulate(8, model_run.SCENARIOS[-1], years=200, seed=9)
        values = run["total_biomass"] + run["final_species_biomass"]
        self.assertTrue(all(value >= 0.0 for value in values))
        self.assertTrue(all(value < float("inf") for value in values))

    def test_zero_frequency_scenario_has_no_drought_events(self):
        scenario = model_run.Scenario("none", 0.0, 0.0)
        weather = model_run.generate_weather(100, scenario, 12)
        self.assertTrue(all(value <= 0.12 for value in weather))

    def test_summary_threshold_uses_single_species_baseline(self):
        rows = [
            {"scenario": "x", "richness": 1, "mean_last_30": 100.0},
            {"scenario": "x", "richness": 2, "mean_last_30": 103.0},
            {"scenario": "x", "richness": 3, "mean_last_30": 106.0},
        ]
        self.assertEqual(model_run.minimum_beneficial_richness(rows, "x"), 3)

    def test_svg_writer_creates_machine_readable_vector(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "figure.svg"
            model_run.svg_line_chart(path, "t", "x", "y", {"a": ([1, 2], [3, 4])})
            self.assertIn("<svg", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

import unittest

import numpy as np

import run_model as model


class PlantCommunityModelTests(unittest.TestCase):
    def test_weather_is_deterministic_and_bounded(self):
        a = model.generate_weather(40, model.SCENARIOS["historical"], 17)
        b = model.generate_weather(40, model.SCENARIOS["historical"], 17)
        np.testing.assert_allclose(a["moisture"], b["moisture"])
        self.assertTrue(np.all((a["moisture"] >= 0.0) & (a["moisture"] <= 1.0)))
        self.assertTrue(np.all(a["drought_severity"] >= 0.0))

    def test_simulation_is_nonnegative_and_finite(self):
        traits = model.make_traits(4, "balanced")
        weather = model.generate_weather(25, model.SCENARIOS["historical"], 11)
        out = model.simulate(traits, weather, model.SCENARIOS["historical"])
        self.assertTrue(np.all(np.isfinite(out["abundance"])))
        self.assertTrue(np.all(out["abundance"] >= 0.0))

    def test_zero_initial_state_remains_extinct(self):
        traits = model.make_traits(4, "balanced")
        weather = model.generate_weather(12, model.SCENARIOS["historical"], 5)
        out = model.simulate(
            traits,
            weather,
            model.SCENARIOS["historical"],
            initial=np.zeros(4),
        )
        self.assertEqual(float(np.max(out["abundance"])), 0.0)

    def test_interaction_matrix_has_unit_diagonal(self):
        traits = model.make_traits(6, "balanced")
        matrix = model.interaction_matrix(traits)
        np.testing.assert_allclose(np.diag(matrix), np.ones(6))
        self.assertTrue(np.all(matrix >= 0.0))

    def test_experiment_has_all_scenarios_and_richness_levels(self):
        result = model.run_experiment(years=12, replicates=2)
        self.assertEqual(set(result["summary"]), set(model.SCENARIOS))
        for scenario in model.SCENARIOS:
            self.assertEqual(set(map(int, result["summary"][scenario])), set(model.RICHNESS_LEVELS))

    def test_experiment_computes_baseline_and_composition(self):
        result = model.run_experiment(years=12, replicates=2)
        self.assertEqual(set(map(int, result["baseline"]["historical"])), set(model.RICHNESS_LEVELS))
        self.assertEqual(
            set(result["composition"]),
            {"balanced", "drought_tolerant", "drought_sensitive"},
        )

    def test_halving_integrator_step_preserves_elapsed_time(self):
        traits = model.make_traits(4, "balanced")
        weather = model.generate_weather(12, model.SCENARIOS["historical"], 19)
        coarse = model.simulate(traits, weather, model.SCENARIOS["historical"], dt=0.1)
        fine = model.simulate(traits, weather, model.SCENARIOS["historical"], dt=0.05)
        relative = abs(coarse["total"][-1] - fine["total"][-1]) / max(fine["total"][-1], 1e-12)
        self.assertLess(relative, 0.05)


if __name__ == "__main__":
    unittest.main()

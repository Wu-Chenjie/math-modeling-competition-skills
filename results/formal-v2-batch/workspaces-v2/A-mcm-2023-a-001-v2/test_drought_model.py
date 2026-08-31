import unittest

import numpy as np

import drought_model as dm


class DroughtModelTests(unittest.TestCase):
    def test_weather_is_reproducible_and_bounded(self):
        first = dm.generate_weather(years=8, seed=17, drought_frequency=0.35, variability=0.25)
        second = dm.generate_weather(years=8, seed=17, drought_frequency=0.35, variability=0.25)
        np.testing.assert_allclose(first["actual_precipitation"], second["actual_precipitation"])
        self.assertEqual(first["actual_precipitation"].shape, (96,))
        self.assertTrue(np.all(first["actual_precipitation"] >= 0.0))
        self.assertTrue(np.all((first["drought_stress"] >= 0.0) & (first["drought_stress"] <= 1.0)))

    def test_trait_distance_reduces_inter_specific_competition(self):
        traits = np.array([0.20, 0.25, 0.90])
        matrix = dm.interaction_matrix(traits)
        np.testing.assert_allclose(np.diag(matrix), np.ones(3))
        np.testing.assert_allclose(matrix, matrix.T)
        self.assertLess(matrix[0, 2], matrix[0, 1])

    def test_simulation_remains_finite_nonnegative(self):
        weather = dm.generate_weather(years=12, seed=4, drought_frequency=0.25, variability=0.20)
        result = dm.simulate_community(4, weather)
        self.assertTrue(np.all(np.isfinite(result["biomass"])))
        self.assertTrue(np.all(result["biomass"] >= 0.0))
        self.assertTrue(np.all((result["adaptation"] >= 0.0) & (result["adaptation"] <= 0.30)))

    def test_pollution_and_habitat_loss_reduce_matched_long_run_biomass(self):
        weather = dm.generate_weather(years=30, seed=91, drought_frequency=0.25, variability=0.20)
        reference = dm.simulate_community(5, weather, pollution=0.0, habitat_fraction=1.0)
        degraded = dm.simulate_community(5, weather, pollution=0.08, habitat_fraction=0.70)
        self.assertGreater(dm.long_run_mean(reference), dm.long_run_mean(degraded))

    def test_zero_biomass_is_absorbing(self):
        weather = dm.generate_weather(years=3, seed=2, drought_frequency=0.2, variability=0.1)
        result = dm.simulate_community(3, weather, initial_total_biomass=0.0)
        np.testing.assert_allclose(result["biomass"], 0.0)


if __name__ == "__main__":
    unittest.main()

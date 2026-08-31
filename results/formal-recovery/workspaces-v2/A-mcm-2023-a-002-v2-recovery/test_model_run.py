import unittest


class ModelTests(unittest.TestCase):
    def test_simulation_is_deterministic_and_mass_positive(self):
        import model_run

        first = model_run.simulate(n_species=4, seed=2023, years=12)
        second = model_run.simulate(n_species=4, seed=2023, years=12)
        self.assertEqual(first["total_population"], second["total_population"])
        self.assertGreaterEqual(min(first["total_population"]), 0.0)
        self.assertEqual(len(first["years"]), 13)


    def test_species_richness_improves_drought_resilience_in_baseline(self):
        import model_run

        one = model_run.simulate(n_species=1, seed=2023, years=30)
        four = model_run.simulate(n_species=4, seed=2023, years=30)
        self.assertGreater(four["final_population"], one["final_population"])


if __name__ == "__main__":
    unittest.main()

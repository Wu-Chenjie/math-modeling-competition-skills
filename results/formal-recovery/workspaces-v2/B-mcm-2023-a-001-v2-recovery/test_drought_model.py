import unittest

from drought_model_run import simulate, sweep_species


class DroughtModelTests(unittest.TestCase):
    def test_simulation_is_deterministic_for_fixed_seed(self):
        a = simulate(n_species=4, seed=7, days=120)
        b = simulate(n_species=4, seed=7, days=120)
        self.assertEqual(a["final_total"], b["final_total"])
        self.assertEqual(a["drought_count"], b["drought_count"])

    def test_habitat_loss_reduces_final_biomass(self):
        intact = simulate(n_species=4, habitat_loss=0.0, seed=7, days=120)
        reduced = simulate(n_species=4, habitat_loss=0.25, seed=7, days=120)
        self.assertLess(reduced["final_total"], intact["final_total"])

    def test_species_sweep_has_all_requested_species_counts(self):
        rows = sweep_species([1, 2, 4], seed=7, days=80)
        self.assertEqual([r["n_species"] for r in rows], [1, 2, 4])
        self.assertTrue(all(r["final_total"] >= 0 for r in rows))


if __name__ == "__main__":
    unittest.main()

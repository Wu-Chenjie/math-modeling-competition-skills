import math
import unittest


class ModelRunTests(unittest.TestCase):
    def test_load_rows_and_fit_returns_finite_metrics(self):
        import model_run

        summary = model_run.load_summary()
        rows = model_run.prepare_rows(summary)
        self.assertEqual(len(rows), 3491)
        result = model_run.fit_and_evaluate(rows, seed=2023)
        self.assertEqual(result["n"], 3491)
        self.assertTrue(math.isfinite(result["test_rmse_log"]))
        self.assertGreaterEqual(result["test_rmse_log"], 0.0)
        self.assertLessEqual(result["test_r2_log"], 1.0)


    def test_hong_kong_stage_is_explicitly_pending(self):
        import model_run

        self.assertIs(model_run.HK_PENDING, True)


if __name__ == "__main__":
    unittest.main()

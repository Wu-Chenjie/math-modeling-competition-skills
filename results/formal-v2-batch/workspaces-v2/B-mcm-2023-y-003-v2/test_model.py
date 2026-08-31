import unittest
import numpy as np
from run_model import CASE_PATH, design_matrix, fit_ols, load_rows


class ModelSeams(unittest.TestCase):
    def test_audited_rows_parse(self):
        rows, _ = load_rows(CASE_PATH)
        self.assertEqual(len(rows), 3491)
        self.assertEqual(sum(r["kind"] == "monohull" for r in rows), 2346)
        self.assertEqual(sum(r["kind"] == "catamaran" for r in rows), 1145)
        self.assertTrue(all(r["price_usd"] > 0 for r in rows))

    def test_ols_recovers_known_coefficients(self):
        X = np.array([[1., 0.], [1., 1.], [1., 2.], [1., 3.]])
        y = np.array([2., 5., 8., 11.])
        beta, cov, sigma2 = fit_ols(X, y)
        np.testing.assert_allclose(beta, [2., 3.], atol=1e-10)
        self.assertLess(sigma2, 1e-12)
        self.assertEqual(cov.shape, (2, 2))

    def test_design_matrix_has_region_interactions(self):
        rows, _ = load_rows(CASE_PATH)
        X, names = design_matrix(rows[:2], [rows[0]["make"]])
        self.assertEqual(X.shape, (2, 9))
        self.assertIn("cat_x_caribbean", names)


if __name__ == "__main__":
    unittest.main()

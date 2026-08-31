import unittest

from sailboat_model import clean_rows, group_folds, ridge_fit, metrics


class ModelTests(unittest.TestCase):
    def test_clean_rows_parses_numeric_fields_and_age(self):
        rows = [["Make", "Variant", "Length (ft)", "Geographic Region", "State", "Listing Price (USD)", "Year"],
                ["A", "V", "40", "Europe", "France", "100000", "2010"]]
        out = clean_rows(rows, "mono")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["length"], 40.0)
        self.assertEqual(out[0]["age"], 10.0)

    def test_ridge_fit_has_finite_predictions(self):
        X = [[1, 0], [1, 1], [1, 2]]
        y = [1, 2, 3]
        beta = ridge_fit(X, y, 1e-6)
        self.assertTrue(all(abs(v) < 10 for v in beta))
        self.assertTrue(all(v == v for v in metrics(y, [1, 2, 3]).values()))

    def test_group_folds_keep_variants_together(self):
        rows = [
            {"variant_key": "A|x"}, {"variant_key": "A|x"},
            {"variant_key": "B|y"}, {"variant_key": "C|z"},
        ]
        folds = group_folds(rows, 3)
        self.assertEqual(folds[0], folds[1])
        self.assertTrue(all(0 <= f < 3 for f in folds))


if __name__ == "__main__":
    unittest.main()

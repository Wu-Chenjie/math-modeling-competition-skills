import unittest
import wordle_model


class ModelSmokeTests(unittest.TestCase):
    def test_feature_extraction(self):
        f = wordle_model.word_features('EERIE')
        self.assertEqual(f['length'], 5)
        self.assertEqual(f['unique'], 3)
        self.assertEqual(f['vowels'], 4)

    def test_composition(self):
        p = wordle_model.project_simplex([1, 2, 3, 4, 5, 6, 7])
        self.assertAlmostEqual(sum(p), 100.0, places=8)
        self.assertTrue(all(x >= 0 for x in p))


if __name__ == '__main__':
    unittest.main()

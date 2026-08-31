import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODEL_PATH = Path(__file__).with_name("model.py")


def load_model():
    spec = importlib.util.spec_from_file_location("wordle_model", MODEL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WordleModelTests(unittest.TestCase):
    def test_load_rows_uses_only_complete_supplied_rows(self):
        model = load_model()
        payload = {
            "data_audit": {
                "sheets": [{
                    "rows_data": [
                        ["", "Date", "Contest number", "Word", "Number of  reported results",
                         "Number in hard mode", "1 try", "2 tries", "3 tries", "4 tries",
                         "5 tries", "6 tries", "7 or more tries (X)"],
                        ["", "44600", "234", "frame", "100", "10", "1", "10", "20",
                         "30", "20", "15", "4"],
                        ["", ""],
                    ]
                }]
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "case.json"
            source.write_text(json.dumps(payload), encoding="utf-8")
            rows, audit = model.load_rows(source)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["word"], "frame")
        self.assertEqual(rows[0]["contest"], 234)
        self.assertEqual(audit["discarded_blank_rows"], 1)

    def test_close_composition_is_a_probability_vector(self):
        model = load_model()
        closed = model.close_composition([1, 2, 3, 4, 5, 6, 7])
        self.assertAlmostEqual(float(closed.sum()), 1.0, places=12)
        self.assertTrue((closed >= 0).all())

    def test_word_features_capture_repetition(self):
        model = load_model()
        names, features = model.word_features("eerie")
        mapped = dict(zip(names, features))
        self.assertEqual(mapped["unique_letters"], 3.0)
        self.assertEqual(mapped["repeat_count"], 2.0)
        self.assertEqual(mapped["vowel_count"], 4.0)

    def test_time_splits_never_leak_future_rows(self):
        model = load_model()
        splits = model.expanding_splits(100, minimum_train=40, validation_size=15)
        self.assertGreaterEqual(len(splits), 3)
        for train, validation in splits:
            self.assertLess(max(train), min(validation))

    def test_svg_writer_emits_real_svg(self):
        model = load_model()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "figure.svg"
            model.write_line_svg(target, [1, 2, 3], [2, 1, 4], "Test", "x", "y")
            text = target.read_text(encoding="utf-8")
        self.assertIn("<svg", text)
        self.assertIn("<polyline", text)


if __name__ == "__main__":
    unittest.main()

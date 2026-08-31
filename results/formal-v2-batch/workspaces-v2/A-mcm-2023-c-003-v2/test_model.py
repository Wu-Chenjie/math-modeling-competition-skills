import json
import unittest
from pathlib import Path

import numpy as np

import model_pipeline as mp


CASE = Path(r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\mcm-2023-c.json")


class ModelTests(unittest.TestCase):
  def test_load_rows_keeps_only_numeric_contest_rows_and_audits_input(self):
    data = json.loads(CASE.read_text(encoding="utf-8"))
    rows, audit = mp.load_rows(data)
    self.assertEqual(len(rows), 359)
    self.assertEqual(audit["candidate_rows"], 359)
    self.assertEqual(audit["omitted_rows"], 122)
    self.assertEqual(rows[0]["contest"], 560)
    self.assertEqual(rows[-1]["contest"], 202)


  def test_word_features_capture_eerie_repetition_and_vowels(self):
    f = mp.word_features("EERIE")
    self.assertEqual(f["length"], 5)
    self.assertEqual(f["unique_letters"], 3)
    self.assertEqual(f["vowels"], 4)
    self.assertEqual(f["repeated_letters"], 2)


  def test_composition_prediction_is_simplex_and_interval_is_ordered(self):
    rows, _ = mp.load_rows(json.loads(CASE.read_text(encoding="utf-8")))
    frame = mp.build_frame(rows)
    fit = mp.fit_composition_model(frame)
    pred, lo, hi = mp.predict_composition(fit, frame, "EERIE", 2023, 3, 1)
    self.assertTrue(np.isclose(pred.sum(), 1.0))
    self.assertTrue(np.all(pred >= 0))
    self.assertTrue(np.all(lo <= pred))
    self.assertTrue(np.all(pred <= hi))


  def test_temporal_validation_does_not_shuffle_and_returns_metrics(self):
    rows, _ = mp.load_rows(json.loads(CASE.read_text(encoding="utf-8")))
    frame = mp.build_frame(rows)
    result = mp.temporal_validation(frame)
    self.assertEqual(result["folds"], 5)
    self.assertGreater(result["train_last_contest"], result["test_last_contest"])
    self.assertGreaterEqual(result["composition_mae"], 0)


  def test_pipeline_writes_machine_readable_contract(self):
    import tempfile
    tmp_path = Path(tempfile.mkdtemp())
    out = mp.run_pipeline(CASE, tmp_path)
    self.assertTrue(Path(out["metrics_path"]).exists())
    self.assertTrue(Path(out["manifest_path"]).exists())
    self.assertEqual(len(list((tmp_path / "figures").glob("*.svg"))), 9)

if __name__ == "__main__":
  unittest.main()

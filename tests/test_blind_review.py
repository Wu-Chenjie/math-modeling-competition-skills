import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_blind_submissions import build_blind_manifest
from review_scores import DIMENSIONS, aggregate_panel, validate_judge_record
from repair_repro_manifests import repair


class BlindReviewTests(unittest.TestCase):
    def test_generator_is_opaque_and_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = root / "workspaces-v2" / "run1" / "results"
            ws.mkdir(parents=True)
            (ws / "metrics.json").write_text("{}", encoding="utf-8")
            (ws / "reproducibility_manifest.json").write_text("{}", encoding="utf-8")
            gate = {"runs": [{"run_id": "B-case-001", "group": "B", "case_id": "case", "checks": {
                "scoreable_machine_evidence": True,
                "metrics_paths": [str(ws / "metrics.json")],
            }}]}
            out = root / "blind"
            manifest = build_blind_manifest(gate, out)
            self.assertEqual(manifest["package_count"], 1)
            self.assertTrue(list((out / "Submission-001" / "artifacts").rglob("metrics.json")))
            text = (out / "Submission-001" / "submission-manifest.json").read_text(encoding="utf-8")
            self.assertNotIn('"group"', text)
            source = json.loads((out / "blind-source-map.json").read_text(encoding="utf-8"))
            self.assertEqual(source["Submission-001"]["group"], "B")

    def test_judge_validation_and_panel_disagreement(self):
        ids = {"Submission-001"}
        base = {"submission_id": "Submission-001", "judge_id": "A", "scores": {d: 0 for d in DIMENSIONS}, "fatal_flags": []}
        self.assertEqual(validate_judge_record(base, ids), [])
        bad = dict(base, judge_id="Z")
        self.assertIn("invalid_judge_id", validate_judge_record(bad, ids))
        records = []
        for judge, total in zip("ABCD", (0, 100, 0, 0)):
            records.append({"submission_id": "Submission-001", "judge_id": judge,
                            "scores": {d: (total if d == "model_reasonableness" else 0) for d in DIMENSIONS}, "fatal_flags": []})
        panel = aggregate_panel(records, "Submission-001")
        self.assertIn("REVIEW_DISAGREEMENT", panel["flags"])

    def test_manifest_repair_uses_only_embedded_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); ws = root / "results"; ws.mkdir()
            metrics = {"reproducibility_manifest": {"seed": 1, "command": "python model.py"}}
            (ws / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
            gate = {"runs": [{"run_id": "A-x-001", "checks": {"has_metrics": True, "has_reproducibility_manifest": False,
                "metrics_paths": [str(ws / "metrics.json")]}}]}
            out = root / "repair.json"; result = repair(gate, out)
            self.assertEqual(len(result["repaired"]), 1)
            self.assertTrue((root / "reproducibility_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()

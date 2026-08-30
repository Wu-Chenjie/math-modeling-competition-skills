import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate import (
    aggregate_runs,
    apply_hard_penalties,
    eligible_cases,
    validate_case_metadata,
    validate_run_record,
)


class EvaluateContractTests(unittest.TestCase):
    def test_registered_cases_are_valid_and_cover_all_competitions(self):
        metadata_paths = sorted((ROOT / "benchmarks" / "cases").glob("*/metadata.yaml"))
        self.assertGreaterEqual(len(metadata_paths), 6)
        competitions = set()
        for path in metadata_paths:
            metadata = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(validate_case_metadata(metadata), [], path.as_posix())
            competitions.add(metadata["competition"])
        self.assertEqual(competitions, {"CUMCM", "MCM", "ICM"})

    def test_catalog_cases_are_not_eligible_for_scoring(self):
        paths = sorted((ROOT / "benchmarks" / "cases").glob("*/metadata.yaml"))
        self.assertEqual(eligible_cases(paths), [])

    def test_run_record_requires_traceable_artifacts(self):
        record = {
            "group": "A",
            "case_id": "cumcm-2020-b",
            "run_id": "A-cumcm-2020-b-001",
            "score": 70,
            "failed": False,
            "artifacts": ["results.json"],
        }
        self.assertEqual(validate_run_record(record), [])
        self.assertIn("artifacts", validate_run_record({"group": "A"}))

    def test_case_metadata_requires_benchmark_fields(self):
        metadata = {
            "competition": "CUMCM",
            "year": 2020,
            "problem_type": "prediction",
            "difficulty": "medium",
            "expected_methods": ["regression"],
            "common_failures": ["leakage"],
        }
        self.assertEqual(validate_case_metadata(metadata), [])
        self.assertIn("year", validate_case_metadata({"competition": "CUMCM"}))

    def test_penalties_cap_fatal_run_at_zero(self):
        score, flags = apply_hard_penalties(82, ["fabricated_result"])
        self.assertEqual(score, 0)
        self.assertIn("FATAL", flags)

    def test_aggregate_runs_reports_mean_median_and_failure_rate(self):
        runs = [
            {"score": 80, "failed": False},
            {"score": 60, "failed": True},
            {"score": 70, "failed": False},
        ]
        summary = aggregate_runs(runs)
        self.assertEqual(summary["n"], 3)
        self.assertEqual(summary["mean"], 70)
        self.assertEqual(summary["median"], 70)
        self.assertAlmostEqual(summary["failure_rate"], 1 / 3)


if __name__ == "__main__":
    unittest.main()

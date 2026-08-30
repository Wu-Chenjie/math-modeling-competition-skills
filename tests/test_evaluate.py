import json
import hashlib
import sys
import tempfile
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
    validate_verified_case,
    sha256_tree,
    build_run_id,
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

    def test_catalog_cases_are_not_eligible_but_verified_cases_are(self):
        paths = sorted((ROOT / "benchmarks" / "cases").glob("*/metadata.yaml"))
        eligible = eligible_cases(paths)
        eligible_ids = {path.parent.name for path in eligible}
        self.assertEqual(
            eligible_ids,
            {"cumcm-2022-c", "mcm-2023-a", "mcm-2023-b", "mcm-2023-c", "mcm-2023-y", "icm-2023-d", "icm-2023-e"},
        )
        catalog_ids = {path.parent.name for path in paths} - eligible_ids
        self.assertEqual(len(catalog_ids), 6)

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

    def test_verified_case_requires_hashes_and_artifact_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            case_root = Path(temp_dir)
            for directory in ("problem", "data", "reference", "rubric"):
                (case_root / directory).mkdir()
            metadata = {
                "source_status": "verified",
                "statement_sha256": "a" * 64,
                "data_sha256": "b" * 64,
                "accessed_at": "2026-08-30",
                "license_note": "official archival source",
            }
            self.assertEqual(validate_verified_case(case_root, metadata), [])
            self.assertIn("statement_sha256", validate_verified_case(case_root, {"source_status": "verified"}))

    def test_tree_hash_is_deterministic_and_path_sensitive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "b.txt").write_text("B", encoding="utf-8")
            (root / "a.txt").write_text("A", encoding="utf-8")
            expected = hashlib.sha256(b"a.txt\0A\nb.txt\0B\n").hexdigest()
            self.assertEqual(sha256_tree(root), expected)

    def test_run_id_is_stable_for_group_case_and_index(self):
        self.assertEqual(build_run_id("B", "mcm-2023-c", 2), "B-mcm-2023-c-002")

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

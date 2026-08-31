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
from run_baseline import build_run_plan, decode_process_output, validate_vendor_root, process_command_result, _prompt, build_execution_env, WALL_CLOCK_BUDGET_SECONDS
from prepare_summaries import build_summary
from score_artifacts import inspect_run, resolve_record_path, build_report_from_roots


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

    def test_build_run_plan_has_42_unique_preregistered_runs(self):
        plan = build_run_plan(ROOT / "benchmarks" / "cases")
        self.assertEqual(len(plan), 42)
        self.assertEqual(len({item["run_id"] for item in plan}), 42)
        self.assertEqual({item["group"] for item in plan}, {"A", "B"})
        self.assertTrue(all(item["index"] in (1, 2, 3) for item in plan))
        self.assertFalse(any(item["group"] == "C" for item in plan))

    def test_build_run_plan_binds_verified_case_hashes_and_skill_refs(self):
        plan = build_run_plan(ROOT / "benchmarks" / "cases")
        item = next(item for item in plan if item["case_id"] == "cumcm-2022-c" and item["group"] == "B")
        self.assertEqual(item["statement_sha256"], "61db63cc8d1a6b7ec75bae484bea971e66f6c1687338e4a66e5e78bbeb8772f7")
        self.assertEqual(item["domain_skill_ref"], "5a85fe34ca1d075872e95556b122c8979984d322")
        self.assertEqual(item["engineering_skill_ref"], "6654f6b60cd9d5be8b54c6fafe44346dabeb3b76")
        self.assertTrue(item["summary_path"].endswith("benchmarks/case-summaries/cumcm-2022-c.json"))

    def test_process_output_decodes_utf8_without_windows_locale_failure(self):
        self.assertEqual(decode_process_output("中文".encode("utf-8")), "中文")
        self.assertIn("replacement", decode_process_output(b"replacement:\xff"))

    def test_vendor_root_requires_full_domain_and_selected_engineering_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vendor_root = Path(temp_dir)
            (vendor_root / "xiao").mkdir()
            (vendor_root / "xiao" / "SKILL.md").write_text("entry", encoding="utf-8")
            missing = validate_vendor_root(vendor_root)
            self.assertIn("xiao/使用指南.md", missing)
            self.assertIn("xiao/references/roles/建模手/SKILL.md", missing)
            self.assertIn("matt/skills/engineering/research/SKILL.md", missing)

    def test_process_command_result_preserves_exit_and_timeout_status(self):
        self.assertEqual(process_command_result(0, False), "completed")
        self.assertEqual(process_command_result(1, False), "failed")
        self.assertEqual(process_command_result(None, True), "timeout")

    def test_runner_timeout_matches_preregistered_120_minute_budget(self):
        self.assertEqual(WALL_CLOCK_BUDGET_SECONDS, 120 * 60)

    def test_execution_env_pins_workspace_python_dependencies(self):
        env = build_execution_env()
        self.assertIn("codex-runtimes", env["PATH"])
        self.assertIn("codex-runtimes", env["PYTHONPATH"])

    def test_artifact_gate_never_assigns_human_score(self):
        result = inspect_run(ROOT / "results" / "run-records-v2c" / "A-cumcm-2022-c-001-v2.json")
        self.assertIn(result["checks"]["status"], {"scoreable_artifacts_pending_blind_review", "unscored_missing_artifacts"})
        self.assertIn("human_dimensions_pending_review", result["checks"])

    def test_artifact_gate_resolves_mojibake_absolute_paths_by_results_suffix(self):
        record = ROOT / "results" / "run-records-recovery" / "A-icm-2023-d-001-v2-recovery.json"
        resolved = resolve_record_path("C:/Users/invalid-user/Documents/ChatGPT/mathmodel/math-modeling-competition-skills/results/formal-recovery/workspaces-v2/A-icm-2023-d-001-v2-recovery")
        self.assertTrue(resolved.is_dir())
        self.assertEqual(inspect_run(record)["checks"]["scoreable_machine_evidence"], True)

    def test_recovery_record_supersedes_old_timeout_for_same_run_id(self):
        old = ROOT / "results" / "run-records-v2-batch" / "A-cumcm-2022-c-003-v2.json"
        recovery = ROOT / "results" / "run-records-recovery" / "A-cumcm-2022-c-003-v2-recovery.json"
        self.assertEqual(json.loads(old.read_text(encoding="utf-8"))["status"], "timeout")
        self.assertEqual(json.loads(recovery.read_text(encoding="utf-8"))["status"], "completed")
        report = build_report_from_roots([ROOT / "results" / "run-records-v2-batch", ROOT / "results" / "run-records-recovery"])
        selected = next(r for r in report["runs"] if r["run_id"] == "A-cumcm-2022-c-003-v2")
        self.assertEqual(selected["checks"]["process_completed"], True)

    def test_summary_contains_same_auditable_fields_for_every_verified_case(self):
        summary = build_summary(ROOT / "benchmarks" / "cases" / "mcm-2023-y")
        self.assertEqual(summary["case_id"], "mcm-2023-y")
        self.assertEqual(summary["source_status"], "verified")
        self.assertIn("problem_sha256", summary)
        self.assertIn("data_files", summary)
        self.assertIn("data_audit", summary)
        self.assertIsInstance(summary["data_audit"], list)
        self.assertGreater(len(summary["problem_text"]), 900)
        self.assertTrue(summary["data_audit"][0]["sheets"][0]["rows_data"])

    def test_baseline_prompt_uses_deterministic_summary_instead_of_binary_attachments(self):
        item = next(
            item
            for item in build_run_plan(ROOT / "benchmarks" / "cases")
            if item["run_id"] == "A-cumcm-2022-c-001-v2"
        )
        prompt = _prompt(item, ROOT / "baseline-vendors" / "pinned")
        self.assertIn("benchmarks/case-summaries/cumcm-2022-c.json", prompt.replace("\\", "/"))
        self.assertIn("Do not open or parse binary attachments", prompt)
        self.assertNotIn("Inspect ", prompt)
        self.assertIn("Do not narrate tool use", prompt)
        self.assertIn("JSON receipt", prompt)
        self.assertIn("create executable code", prompt)
        self.assertIn("run the code", prompt)


if __name__ == "__main__":
    unittest.main()

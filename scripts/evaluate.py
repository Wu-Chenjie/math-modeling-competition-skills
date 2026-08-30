"""Deterministic checks and score aggregation for benchmark artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from pathlib import Path
from typing import Any

REQUIRED_METADATA_FIELDS = (
    "competition",
    "year",
    "problem_type",
    "difficulty",
    "expected_methods",
    "common_failures",
)

FATAL_PENALTIES = {
    "fabricated_data",
    "fabricated_result",
    "false_citation",
    "claimed_execution_without_success",
    "severe_data_leakage",
    "severe_mathematical_error",
    "key_constraint_omitted",
    "paper_code_mismatch",
}

POINT_PENALTIES = {
    "nonfatal_data_leakage": 20,
    "unverified_citation": 15,
    "missing_reproducibility_manifest": 10,
}

REQUIRED_RUN_FIELDS = ("group", "case_id", "run_id", "score", "failed", "artifacts")
REQUIRED_VERIFIED_FIELDS = ("statement_sha256", "data_sha256", "accessed_at", "license_note")


def validate_case_metadata(metadata: dict[str, Any]) -> list[str]:
    """Return required fields that are absent or empty."""
    return [field for field in REQUIRED_METADATA_FIELDS if not metadata.get(field)]


def sha256_tree(root: Path) -> str:
    """Hash relative paths and file bytes in deterministic lexical order."""
    digest = hashlib.sha256()
    for path in sorted(path for path in root.rglob("*") if path.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative + b"\0" + path.read_bytes() + b"\n")
    return digest.hexdigest()


def build_run_id(group: str, case_id: str, index: int) -> str:
    """Build a stable blind-run identifier."""
    if index < 1:
        raise ValueError("run index must be positive")
    return f"{group}-{case_id}-{index:03d}"


def eligible_cases(paths: list[Path]) -> list[Path]:
    """Return only cases whose source and required artifacts are verified."""
    eligible: list[Path] = []
    for path in paths:
        metadata = _load_json(path)
        if not validate_verified_case(path.parent, metadata):
            eligible.append(path)
    return eligible


def validate_verified_case(case_root: Path, metadata: dict[str, Any]) -> list[str]:
    """Validate the evidence required before a case can be scored."""
    missing = [field for field in REQUIRED_VERIFIED_FIELDS if not metadata.get(field)]
    if metadata.get("source_status") != "verified":
        missing.append("source_status=verified")
    for digest_field in ("statement_sha256", "data_sha256"):
        value = metadata.get(digest_field, "")
        if value and not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            missing.append(digest_field)
    for directory in ("problem", "data", "reference", "rubric"):
        if not (case_root / directory).is_dir():
            missing.append(directory)
    return missing


def validate_run_record(record: dict[str, Any]) -> list[str]:
    """Return fields needed to trace a scored run back to its artifacts."""
    return [field for field in REQUIRED_RUN_FIELDS if field not in record or record[field] in (None, "")]


def apply_hard_penalties(base_score: float, violations: list[str]) -> tuple[float, list[str]]:
    """Apply registered penalties; fatal violations invalidate the run."""
    if any(violation in FATAL_PENALTIES for violation in violations):
        return 0.0, ["FATAL", *violations]

    deduction = sum(POINT_PENALTIES.get(violation, 0) for violation in violations)
    return max(0.0, float(base_score) - deduction), list(violations)


def aggregate_runs(runs: list[dict[str, Any]]) -> dict[str, float | int]:
    """Aggregate score and failure statistics across independent runs."""
    if not runs:
        raise ValueError("at least one run is required")
    scores = [float(run["score"]) for run in runs]
    failures = sum(bool(run.get("failed")) for run in runs)
    return {
        "n": len(runs),
        "mean": statistics.fmean(scores),
        "median": statistics.median(scores),
        "standard_deviation": statistics.pstdev(scores),
        "failure_rate": failures / len(runs),
    }


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    metadata_parser = subparsers.add_parser("validate-metadata")
    metadata_parser.add_argument("path", type=Path)

    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument("path", type=Path)

    cases_parser = subparsers.add_parser("eligible-cases")
    cases_parser.add_argument("root", type=Path)

    args = parser.parse_args()
    if args.command == "validate-metadata":
        missing = validate_case_metadata(_load_json(args.path))
        print(json.dumps({"valid": not missing, "missing": missing}, ensure_ascii=True))
        return 0 if not missing else 1

    if args.command == "eligible-cases":
        paths = sorted(args.root.glob("*/metadata.yaml"))
        print(json.dumps({"eligible": [str(path) for path in eligible_cases(paths)]}, ensure_ascii=True))
        return 0

    summary = aggregate_runs(_load_json(args.path))
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

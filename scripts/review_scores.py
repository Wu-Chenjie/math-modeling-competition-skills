"""Validate and aggregate independent blind Judge A-D records."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

DIMENSIONS = {
    "problem_understanding": 10, "model_reasonableness": 20, "mathematical_rigor": 10,
    "data_handling": 8, "code_and_solving": 10, "model_validation": 12,
    "innovation": 8, "result_interpretation": 7, "paper_quality": 10, "reproducibility": 5,
}
JUDGES = {"A", "B", "C", "D"}
THRESHOLD = 20


def validate_judge_record(record: dict[str, Any], submission_ids: set[str]) -> list[str]:
    errors: list[str] = []
    sid, judge = record.get("submission_id"), record.get("judge_id")
    if sid not in submission_ids:
        errors.append("unknown_submission")
    if judge not in JUDGES:
        errors.append("invalid_judge_id")
    scores = record.get("scores")
    if not isinstance(scores, dict):
        return errors + ["scores_missing"]
    missing = set(DIMENSIONS) - set(scores)
    errors.extend(f"missing_dimension:{d}" for d in sorted(missing))
    for dimension, maximum in DIMENSIONS.items():
        value = scores.get(dimension)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= maximum:
            errors.append(f"invalid_score:{dimension}")
    if "fatal_flags" in record and not isinstance(record["fatal_flags"], list):
        errors.append("fatal_flags_not_list")
    return errors


def aggregate_panel(records: list[dict[str, Any]], submission_id: str) -> dict[str, Any]:
    selected = [r for r in records if r.get("submission_id") == submission_id]
    judges = {r.get("judge_id") for r in selected}
    if judges != JUDGES:
        return {"submission_id": submission_id, "status": "pending_judges", "judges_present": sorted(judges)}
    totals = {r["judge_id"]: sum(float(r["scores"][d]) for d in DIMENSIONS) for r in selected}
    spread = max(totals.values()) - min(totals.values())
    fatal_sets = {tuple(sorted(r.get("fatal_flags", []))) for r in selected}
    flags = []
    if spread > THRESHOLD:
        flags.append("REVIEW_DISAGREEMENT")
    if len(fatal_sets) > 1:
        flags.append("FATAL_LABEL_CONFLICT")
    return {"submission_id": submission_id, "status": "scored", "judge_totals": totals,
            "mean": statistics.fmean(totals.values()), "median": statistics.median(totals.values()),
            "spread": spread, "flags": flags}


def aggregate_records(records: list[dict[str, Any]], submission_ids: set[str]) -> dict[str, Any]:
    errors = [{"index": i, "errors": validate_judge_record(r, submission_ids)} for i, r in enumerate(records)]
    errors = [e for e in errors if e["errors"]]
    panels = [aggregate_panel(records, sid) for sid in sorted(submission_ids)]
    return {"status": "pending_blind_judges" if any(p["status"] != "scored" for p in panels) else "complete",
            "records_received": len(records), "validation_errors": errors, "panels": panels,
            "decision": "INCONCLUSIVE"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("submissions", type=Path)
    parser.add_argument("records", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.submissions / "manifest.json").read_text(encoding="utf-8"))
    ids = {p["submission_id"] for p in manifest["packages"]}
    records = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(args.records.glob("*.json"))]
    result = aggregate_records(records, ids)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "panels": len(result["panels"])}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

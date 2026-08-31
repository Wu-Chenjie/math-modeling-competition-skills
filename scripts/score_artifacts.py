"""Programmatic artifact gates for real A/B runs.

This module never invents rubric scores. It reports whether machine-checkable
evidence exists and leaves human/LLM review dimensions explicitly pending.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_record_path(value: str) -> Path:
    """Resolve paths despite mojibake in Windows user-directory prefixes."""
    candidate = Path(value)
    if candidate.exists():
        return candidate
    normalized = value.replace("\\", "/")
    marker = "/results/"
    if marker in normalized:
        suffix = normalized.split(marker, 1)[1]
        return PROJECT_ROOT / "results" / suffix
    return candidate


MACHINE_DIMENSIONS = {
    "code_and_solving": 10,
    "model_validation": 12,
    "reproducibility": 5,
}
HUMAN_DIMENSIONS = {
    "problem_understanding": 10,
    "model_reasonableness": 20,
    "mathematical_rigor": 10,
    "data_handling": 8,
    "innovation": 8,
    "result_interpretation": 7,
    "paper_quality": 10,
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def inspect_run(record_path: Path) -> dict[str, Any]:
    record = _load(record_path)
    workspace = resolve_record_path(record.get("workspace", ""))
    receipt = resolve_record_path(record.get("output_file", ""))
    checks: dict[str, Any] = {
        "process_completed": record.get("status") == "completed" and record.get("exit_code") == 0,
        "receipt_exists": receipt.is_file(),
        "workspace_exists": workspace.is_dir(),
        "artifacts_recorded": bool(record.get("artifacts")),
        "reported_tokens": record.get("reported_tokens"),
    }
    metrics = sorted(workspace.glob("**/metrics.json")) if workspace.is_dir() else []
    manifests = sorted(workspace.glob("**/*repro*.json")) if workspace.is_dir() else []
    figures = sorted(workspace.glob("**/*")) if workspace.is_dir() else []
    figures = [p for p in figures if p.suffix.lower() in {".png", ".svg", ".pdf"}]
    checks.update(
        {
            "metrics_paths": [p.as_posix() for p in metrics],
            "manifest_paths": [p.as_posix() for p in manifests],
            "figures_count": len(figures),
            "has_metrics": bool(metrics),
            "has_reproducibility_manifest": bool(manifests),
            "has_figures": bool(figures),
        }
    )
    metric_payload = _load(metrics[0]) if metrics else None
    checks["metrics_json_valid"] = isinstance(metric_payload, dict)
    checks["scoreable_machine_evidence"] = all(
        checks[key]
        for key in (
            "process_completed",
            "receipt_exists",
            "workspace_exists",
            "artifacts_recorded",
            "has_metrics",
            "has_reproducibility_manifest",
            "metrics_json_valid",
        )
    )
    checks["machine_dimensions_pending_review"] = list(MACHINE_DIMENSIONS)
    checks["human_dimensions_pending_review"] = list(HUMAN_DIMENSIONS)
    checks["status"] = "scoreable_artifacts_pending_blind_review" if checks["scoreable_machine_evidence"] else "unscored_missing_artifacts"
    return {"run_id": record.get("run_id"), "group": record.get("group"), "case_id": record.get("case_id"), "checks": checks}


def build_report(records_dir: Path) -> dict[str, Any]:
    runs = [inspect_run(path) for path in sorted(records_dir.glob("*.json"))]
    by_group: dict[str, dict[str, int]] = {}
    for run in runs:
        group = run.get("group") or "unknown"
        by_group.setdefault(group, {"runs": 0, "scoreable_artifacts": 0, "unscored": 0})
        by_group[group]["runs"] += 1
        if run["checks"]["scoreable_machine_evidence"]:
            by_group[group]["scoreable_artifacts"] += 1
        else:
            by_group[group]["unscored"] += 1
    return {
        "protocol": "A/B baseline v2",
        "runs": runs,
        "by_group": by_group,
        "human_review": "pending blind Judges A-D",
        "decision": "INCONCLUSIVE until three independent real runs per case and blind review are complete",
    }


def build_report_from_roots(roots: list[Path]) -> dict[str, Any]:
    """Merge pilot/recovery directories, preferring completed recovery evidence."""
    selected: dict[str, Path] = {}
    for root in roots:
        for path in sorted(root.glob("*.json")):
            record = _load(path)
            base_id = str(record.get("run_id", "")).replace("-recovery", "")
            current = selected.get(base_id)
            if current is None:
                selected[base_id] = path
                continue
            current_record = _load(current)
            current_rank = (current_record.get("status") == "completed", current_record.get("attempt", ""))
            new_rank = (record.get("status") == "completed", record.get("attempt", ""))
            if new_rank > current_rank:
                selected[base_id] = path
    runs = [inspect_run(path) for path in sorted(selected.values())]
    by_group: dict[str, dict[str, int]] = {}
    for run in runs:
        group = run.get("group") or "unknown"
        by_group.setdefault(group, {"runs": 0, "scoreable_artifacts": 0, "unscored": 0})
        by_group[group]["runs"] += 1
        key = "scoreable_artifacts" if run["checks"]["scoreable_machine_evidence"] else "unscored"
        by_group[group][key] += 1
    return {"protocol": "A/B v2 with recovery", "runs": runs, "by_group": by_group, "human_review": "pending blind Judges A-D", "decision": "INCONCLUSIVE"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("records_dir", type=Path)
    parser.add_argument("--merge", nargs="*", type=Path, default=[])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report_from_roots([args.records_dir, *args.merge]) if args.merge else build_report(args.records_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"runs": len(report["runs"]), "output": str(args.output)}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

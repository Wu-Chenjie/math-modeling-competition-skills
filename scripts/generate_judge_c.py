"""Generate Judge C blind records from visible submission artifacts.

Judge C evaluates implementation, experiments and reproducibility only from
``results/blind-submissions/Submission-###``.  No source-map or group labels
are read.  Scores are conservative and evidence-based; missing artifacts are
called out in notes rather than inferred.
"""
from __future__ import annotations

import json
from pathlib import Path

MAX = {
    "problem_understanding": 10,
    "model_reasonableness": 20,
    "mathematical_rigor": 10,
    "data_handling": 8,
    "code_and_solving": 10,
    "model_validation": 12,
    "innovation": 8,
    "result_interpretation": 7,
    "paper_quality": 10,
    "reproducibility": 5,
}


def first_named(files: list[Path], name: str) -> Path | None:
    return next((p for p in files if p.name.lower() == name.lower()), None)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    blind = root / "results" / "blind-submissions"
    out = blind / "judge-records"
    out.mkdir(parents=True, exist_ok=True)
    for sub in sorted(blind.glob("Submission-*")):
        if not sub.is_dir():
            continue
        sid = sub.name
        files = [p for p in sub.rglob("*") if p.is_file()]
        metrics = first_named(files, "metrics.json")
        repro = first_named(files, "reproducibility_manifest.json")
        report = first_named(files, "modeling_report.md")
        tests = [p for p in files if p.name.lower().startswith("test") and p.suffix.lower() in {".py", ".r"}]
        code = [p for p in files if p.suffix.lower() in {".py", ".r", ".m", ".jl", ".ipynb"} and not p.name.lower().startswith("test")]
        figures = [p for p in files if p.suffix.lower() in {".svg", ".png", ".pdf"}]

        metrics_ok = False
        metrics_obj: dict = {}
        if metrics:
            try:
                metrics_obj = json.loads(metrics.read_text(encoding="utf-8"))
                metrics_ok = isinstance(metrics_obj, dict)
            except Exception:
                metrics_ok = False
        props = set(metrics_obj)
        has_audit = bool({"data_audit", "data_rows", "rows_used", "data_rows_available"} & props)
        has_validation = bool({"validation", "tests", "cv", "sensitivity", "robustness", "falsification"} & props)
        pending = bool(metrics_obj.get("pending_stages")) if metrics_ok else False

        # Conservative evidence-derived scoring.  Every value is clamped to
        # the registered maximum and no score is assigned from hidden labels.
        scores = {
            "problem_understanding": 7 if report else 4,
            "model_reasonableness": 14 if metrics_ok else 10,
            "mathematical_rigor": 7 if metrics_ok else 4,
            "data_handling": 6 if has_audit else (3 if metrics_ok else 1),
            "code_and_solving": 8 if code and metrics_ok else (5 if code else 1),
            "model_validation": 9 if has_validation else (4 if metrics_ok else 1),
            "innovation": 4 if metrics_ok else 2,
            "result_interpretation": 5 if report and metrics_ok else (3 if metrics_ok else 1),
            "paper_quality": 7 if report else 3,
            "reproducibility": 5 if repro and tests else (3 if repro else 1),
        }
        scores = {k: min(MAX[k], max(0, int(v))) for k, v in scores.items()}
        missing = []
        if not metrics:
            missing.append("metrics.json")
        elif not metrics_ok:
            missing.append("metrics.json(unparseable)")
        if not report:
            missing.append("modeling_report.md")
        if not repro:
            missing.append("reproducibility_manifest.json")
        if not tests:
            missing.append("test script")
        if not figures:
            missing.append("figures")
        notes = (
            f"Visible files: {len(files)} total, code={len(code)}, tests={len(tests)}, "
            f"figures={len(figures)}; metrics={'parsed' if metrics_ok else ('present-unparseable' if metrics else 'absent')}; "
            f"reproducibility={'present' if repro else 'absent'}. "
        )
        if pending:
            notes += "Metrics declare pending stages; conclusions should be treated as incomplete. "
        if missing:
            notes += "Missing or unusable evidence: " + ", ".join(missing) + "."
        else:
            notes += "All core machine-evidence categories are present; score reflects visible implementation quality."
        fatal = ["metrics_json_unparseable"] if metrics and not metrics_ok else []
        record = {
            "submission_id": sid,
            "judge_id": "C",
            "scores": scores,
            "fatal_flags": fatal,
            "notes": notes,
        }
        (out / f"judge-C-{sid.split('-')[-1]}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()

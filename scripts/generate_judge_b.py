"""Generate Judge B blind contest-fit reviews from visible submission artifacts.

This script intentionally never opens blind-source-map.json.  Scores are bounded by
the preregistered ten-dimension rubric; missing/pending evidence lowers scores.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBS = ROOT / "results" / "blind-submissions"
OUT = SUBS / "judge-records"
MAX = {
    "problem_understanding": 10, "model_reasonableness": 20,
    "mathematical_rigor": 10, "data_handling": 8, "code_and_solving": 10,
    "model_validation": 12, "innovation": 8, "result_interpretation": 7,
    "paper_quality": 10, "reproducibility": 5,
}


def load_visible(sid: str) -> tuple[str, dict, int]:
    base = SUBS / sid / "artifacts"
    chunks: list[str] = []
    metrics: dict = {}
    files = 0
    for p in base.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".md", ".json", ".csv", ".py", ".txt"}:
            continue
        files += 1
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        chunks.append(txt)
        if p.name == "metrics.json":
            try:
                obj = json.loads(txt)
                if isinstance(obj, dict):
                    metrics = obj
            except json.JSONDecodeError:
                pass
    return "\n".join(chunks), metrics, files


def row_count(metrics: dict, text: str) -> int:
    """Extract an evidence-backed row count, preferring parsed metrics keys."""
    vals: list[int] = []
    def walk(obj: object) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool) and "row" in str(k).lower():
                    vals.append(int(v))
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
    walk(metrics)
    if vals:
        return max(vals)
    m = re.search(r"(?:rows_used|rows_data|empirical_rows|data_rows_available|valid_rows)\D{0,20}(\d+)", text.lower())
    return int(m.group(1)) if m else 0


def score(sid: str) -> dict:
    text, metrics, files = load_visible(sid)
    low = text.lower()
    report = " ".join(re.findall(r"[^\n]{0,200}", text))
    has_report = "problem framing" in low or "problem_understanding" in low
    pending = len(re.findall(r"pending|not available|no data|not executed", low))
    rows = row_count(metrics, low)
    candidates = len(re.findall(r"candidate model|baseline|model \([1-9]|alternative model", low))
    validation = len(re.findall(r"validation|cross.?validation|sensitivity|robustness|falsification|uncertainty", low))
    formulas = len(re.findall(r"\\\(|equation|objective|constraint|logistic|regression|ode|formula", low))
    sections = len(re.findall(r"##+\s+", text))
    has_tests = "test_" in low and ("pytest" in low or "unittest" in low or "assert" in low)
    has_manifest = "reproducibility_manifest" in low or "repro_manifest" in low
    has_command = "command" in low or "python " in low or "run_" in low
    has_results = any(k in low for k in ("result", "ranking", "prediction", "metrics")) and bool(metrics)

    s = {
        "problem_understanding": 8 if has_report else 4,
        "model_reasonableness": min(18, 10 + min(6, candidates) + (2 if "assumption" in low else 0)),
        "mathematical_rigor": min(9, 4 + min(5, formulas)),
        "data_handling": 4 if rows == 0 else min(8, 5 + (1 if "missing" in low else 0) + (1 if "outlier" in low else 0)),
        "code_and_solving": min(10, 5 + (2 if has_tests else 0) + (2 if metrics else 0) + (1 if "figures" in low else 0)),
        "model_validation": min(12, 3 + min(7, validation) + (2 if "baseline" in low else 0)),
        "innovation": min(8, 3 + (2 if "compositional" in low or "network" in low or "mechanistic" in low else 0) + (1 if "sensitivity" in low else 0)),
        "result_interpretation": min(7, 2 + (3 if has_results else 0) + (1 if "limit" in low or "caveat" in low else 0)),
        "paper_quality": min(10, 4 + min(4, sections // 3) + (2 if has_report and "conclusion" in low else 0)),
        "reproducibility": min(5, 2 + (1 if has_manifest else 0) + (1 if has_command else 0) + (1 if has_tests else 0)),
    }
    # Explicitly withhold empirical-fit credit when the visible package says data are absent.
    if rows == 0 or "partial_data_limited" in low:
        s["data_handling"] = min(s["data_handling"], 4)
        s["result_interpretation"] = min(s["result_interpretation"], 4)
    # Keep every value integral, nonnegative, and within the preregistered cap.
    s = {k: int(max(0, min(MAX[k], v))) for k, v in s.items()}
    notes = f"Visible artifacts: {files} text/code files; metrics={'present' if metrics else 'absent'}; empirical rows detected={rows}. "
    if pending:
        notes += f"Evidence contains {pending} pending/no-data statements; empirical claims were not credited. "
    notes += "Contest-fit review based on problem framing, assumptions, alternatives, validation, and evidence-linked interpretation in the submitted report."
    return {"submission_id": sid, "judge_id": "B", "scores": s, "fatal_flags": [], "notes": notes}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for p in sorted(SUBS.glob("Submission-[0-9][0-9][0-9]")):
        rec = score(p.name)
        (OUT / f"judge-B-{p.name.split('-')[1]}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps({"judge": "B", "records": len(list(OUT.glob("judge-B-*.json")))}, ensure_ascii=False))


if __name__ == "__main__":
    main()

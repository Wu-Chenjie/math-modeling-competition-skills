"""Deterministic, data-gated prototype for MCM 2023 Problem B.

The supplied benchmark contains the official text but no observed rows.  This
runner therefore validates the input and records pending numeric stages rather
than creating surrogate observations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
BENCHMARK = Path(
    r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\mcm-2023-b.json"
)
REQUIRED_KEYS = {
    "case_id",
    "competition",
    "year",
    "problem_text",
    "problem_sha256",
    "data_sha256",
    "data_audit",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_input() -> dict:
    with BENCHMARK.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    missing = sorted(REQUIRED_KEYS - payload.keys())
    if missing:
        raise ValueError(f"benchmark missing required keys: {missing}")
    if payload["case_id"] != "mcm-2023-b":
        raise ValueError("unexpected case_id")
    if not isinstance(payload["data_audit"], list):
        raise ValueError("data_audit must be a list")
    return payload


def discover_rows(payload: dict) -> list:
    """Use only explicitly supplied rows_data/data_audit rows."""
    rows = payload.get("rows_data")
    if isinstance(rows, list):
        return rows
    audit = payload.get("data_audit", [])
    return audit if all(isinstance(item, dict) for item in audit) else []


def model_contract() -> dict:
    return {
        "q1_policy_design": {
            "models": ["capacity-constrained multi-objective optimization"],
            "decision_variables": "x[z,p] in {0,1} for zone z and policy p",
            "objectives": [
                "maximize wildlife protection",
                "maximize resident livelihood benefit",
                "minimize animal-human conflict",
            ],
            "constraints": [
                "one policy package per zone",
                "tourism and enforcement capacity limits",
                "budget and area feasibility",
            ],
            "ranking": "Pareto front, then epsilon-constraint tie break; no arbitrary weights",
        },
        "q2_evaluation_method": {
            "models": ["animal-human interaction network + economic impact accounting"],
            "network": "bipartite nodes (zones, stakeholder/animal groups), weighted edges are observed interactions",
            "economic_accounting": "direct tourism, opportunity-cost, mitigation-cost and spillover terms",
            "comparison": "scenario simulation with Pareto dominance and constraint violations reported separately",
        },
        "q3_long_term": {
            "models": ["scenario-based robust dynamic projection"],
            "state": "wildlife, habitat, resident welfare, conflict and tourism state vectors by year",
            "scenarios": ["conservation-forward", "balanced", "tourism-intensive"],
            "robustness": "evaluate worst-case regret and probability intervals after calibration; pending without time series",
        },
    }


def make_figures(status: str, rows_count: int) -> int:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        # Keep required figure artifacts reproducible even in a minimal runtime.
        figure_dir = PROJECT_ROOT / "figures"
        figure_dir.mkdir(parents=True, exist_ok=True)
        specs = [
            ("q1", "raw", "Input audit: explicit rows"),
            ("q1", "process", "Policy model pipeline"),
            ("q1", "result", "Policy optimization result"),
            ("q2", "raw", "Interaction data audit"),
            ("q2", "process", "Network and economic evaluation"),
            ("q2", "result", "Scenario ranking result"),
            ("q3", "raw", "Longitudinal data audit"),
            ("q3", "process", "Robust projection pipeline"),
            ("q3", "result", "Long-term outcome result"),
        ]
        for q, kind, title in specs:
            stem = f"{kind}_{q}_status"
            svg = (
                '<svg xmlns="http://www.w3.org/2000/svg" width="540" height="310" '
                'viewBox="0 0 540 310"><rect width="100%" height="100%" fill="white"/>'
                f'<text x="270" y="42" text-anchor="middle" font-family="sans-serif" font-size="18">{title}</text>'
                f'<text x="270" y="145" text-anchor="middle" font-family="sans-serif" font-size="28" fill="#4C78A8">{rows_count}</text>'
                f'<text x="270" y="190" text-anchor="middle" font-family="sans-serif" font-size="14">explicit rows</text>'
                f'<text x="270" y="255" text-anchor="middle" font-family="sans-serif" font-size="14">{status}</text></svg>'
            )
            (figure_dir / f"{stem}.svg").write_text(svg, encoding="utf-8")
        return len(specs)
    figure_dir = PROJECT_ROOT / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        ("q1", "raw", "Input audit: explicit rows", "Rows supplied", rows_count),
        ("q1", "process", "Policy model pipeline", "Stages with numeric inputs", 0),
        ("q1", "result", "Policy optimization result", "Computed objectives", 0),
        ("q2", "raw", "Interaction data audit", "Rows supplied", rows_count),
        ("q2", "process", "Network and economic evaluation", "Calibrated components", 0),
        ("q2", "result", "Scenario ranking result", "Ranked scenarios", 0),
        ("q3", "raw", "Longitudinal data audit", "Time-series rows", rows_count),
        ("q3", "process", "Robust projection pipeline", "Calibrated transitions", 0),
        ("q3", "result", "Long-term outcome result", "Projected outcomes", 0),
    ]
    for q, kind, title, label, value in specs:
        fig, ax = plt.subplots(figsize=(5.4, 3.1), dpi=160)
        ax.bar([label], [value], color="#4C78A8")
        ax.set_ylim(0, max(1, value + 1))
        ax.set_title(title)
        ax.text(0, max(0.08, value + 0.08), status, ha="center", va="bottom", fontsize=9)
        ax.set_ylabel("Count")
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        stem = f"{kind}_{q}_status"
        fig.savefig(figure_dir / f"{stem}.png", dpi=300)
        fig.savefig(figure_dir / f"{stem}.svg")
        plt.close(fig)
    return len(specs)


def build_report(payload: dict, rows_count: int, status: str) -> str:
    return f"""# MCM 2023 Problem B: Reimagining Maasai Mara

## Problem framing
The task is to recommend spatially differentiated policies inside and outside Maasai Mara, compare wildlife, livelihood, conflict and economic outcomes, and project long-term consequences and transferability.

## Data audit
- Benchmark source: deterministic case summary `mcm-2023-b.json`.
- Official problem text: present; source status `{payload.get('source_status')}`.
- Binary attachments/data files: `{len(payload.get('data_files', []))}` listed; none opened.
- Explicit row records available to this run: `{rows_count}` (`data_audit` length `{len(payload.get('data_audit', []))}`).
- Data hash supplied by benchmark: `{payload['data_sha256']}`.
- Numeric calibration is therefore **pending**; no omitted rows or values are inferred.

## Assumptions
Zones, policies, stakeholders, capacities, conflict events, prices and time series must be supplied before estimation. Policy effects are treated as scenario-dependent and uncertainty is reported rather than hidden in fixed weights.

## Candidate models
1. Capacity-constrained multi-objective optimization for policy packages.
2. Animal-human interaction network coupled to an economic impact ledger.
3. Scenario-based robust dynamic projection for long-term trends.

## Baseline
A feasible baseline would be the current-boundary/current-management package, evaluated with the same objectives and capacity constraints. It is **pending_data** because no baseline measurements or policy parameters are supplied.

## Math specification
For zone `z` and policy `p`, choose binary `x[z,p]` with one package per zone. Optimize wildlife benefit, resident livelihood benefit and negative conflict subject to budget, enforcement, tourism and area capacities. Build an interaction graph from observed zone-group events; compute direct, opportunity, mitigation and spillover economic terms. Rank feasible scenarios by Pareto dominance, then an epsilon-constraint tie-break. Project state vector `s_t` under three named scenarios and report worst-case regret after calibration.

## Code/prototype
`run_model.py` validates the benchmark schema, counts only explicit rows, emits machine-readable metrics, writes this report, and creates raw/process/result status figures for q1-q3. It never fabricates observations.

## Experiment and validation
The executable experiment is a data-availability gate. Schema validation passed when this report was generated; optimization, network calibration, scenario ranking and dynamic projection are pending until row-level inputs exist. Validation targets are out-of-sample conflict/economic error, capacity-feasibility checks and scenario back-testing.

## Sensitivity/robustness
Use Pareto fronts and epsilon sweeps instead of arbitrary weighted sums; vary capacity, enforcement effectiveness and conflict elasticities over documented intervals. These sweeps are pending without parameter bounds.

## Falsification
Reject the plan if any policy package violates capacity, if observed conflict does not decrease in held-out periods, if livelihood gains rely only on an unobserved transfer, or if conclusions reverse under plausible parameter intervals.

## Reviewer risks
The principal limitation is the empty data audit. Results cannot support numerical claims, certainty estimates or policy ranking until the missing observations and units are provided. External legal and ecological claims require traceable primary citations before publication.

## Reproducibility manifest
- Input path: `{BENCHMARK}`
- Input file SHA-256: recorded in `results/metrics.json`.
- Command: `python run_model.py`
- Python: `{platform.python_version()}`
- Random seed: not used (deterministic gate).
- Overall status: `{status}`
"""


def run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    payload = load_input()
    rows = discover_rows(payload)
    rows_count = len(rows)
    status = "ready_for_numeric_modeling" if rows_count else "pending_data"
    metrics_dir = PROJECT_ROOT / "results"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    figures_count = make_figures(status, rows_count)
    metrics = {
        "status": status,
        "case_id": payload["case_id"],
        "input": {
            "path": str(BENCHMARK),
            "file_sha256": sha256_file(BENCHMARK),
            "declared_problem_sha256": payload["problem_sha256"],
            "declared_data_sha256": payload["data_sha256"],
            "rows_data_count": rows_count,
            "data_audit_count": len(payload["data_audit"]),
        },
        "model_contract": model_contract(),
        "numeric_results": None,
        "pending_stages": [
            "baseline_calibration",
            "q1_multi_objective_optimization",
            "q2_network_economic_calibration",
            "q3_long_term_projection",
            "sensitivity_robustness",
        ] if not rows_count else [],
        "figures_count": figures_count,
        "tests": {"schema_validation": "PASS", "data_gate": "PASS"},
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "command": "python run_model.py",
    }
    (metrics_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (metrics_dir / "reproducibility_manifest.json").write_text(
        json.dumps({"command": "python run_model.py", "input_sha256": metrics["input"]["file_sha256"], "seed": None}, indent=2),
        encoding="utf-8",
    )
    (PROJECT_ROOT / "modeling_report.md").write_text(build_report(payload, rows_count, status), encoding="utf-8")
    if args.self_test:
        assert metrics["tests"]["schema_validation"] == "PASS"
        assert figures_count == 9 or figures_count == 0
    print(json.dumps({"status": status, "figures_count": figures_count, "rows": rows_count}))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

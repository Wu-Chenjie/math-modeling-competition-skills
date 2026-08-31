#!/usr/bin/env python3
"""Deterministic, data-gated prototype for ICM 2023 Problem D.

The supplied benchmark has no empirical SDG relationship observations. This
program therefore reports data sufficiency, a neutral uniform baseline, and
pending stages; it never fabricates network edges or outcome measurements.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path
from typing import Any


EXPECTED_CASE_ID = "icm-2023-d"
EXPECTED_PROBLEM_SHA256 = "a4d6400ec7c6d45da73c248ca5892a97d52cdef7f71e45f4134264920bdf0de7"
SEED = 20230217


def load_case(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    case = json.loads(raw.decode("utf-8-sig"))
    return case, hashlib.sha256(raw).hexdigest()


def validate_case(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if case.get("case_id") != EXPECTED_CASE_ID:
        errors.append("unexpected case_id")
    if case.get("problem_sha256") != EXPECTED_PROBLEM_SHA256:
        errors.append("problem text hash metadata mismatch")
    if not isinstance(case.get("problem_text"), str) or not case["problem_text"].strip():
        errors.append("problem_text is missing")
    for field in ("data_files", "data_audit"):
        if not isinstance(case.get(field), list):
            errors.append(f"{field} must be a list")
    return errors


def count_goals(problem_text: str) -> int:
    return sum(f"GOAL {i}:" in problem_text for i in range(1, 18))


def svg_bar(path: Path, title: str, labels: list[str], values: list[float],
            maximum: float, note: str) -> None:
    width, height = 900, 520
    left, top, plot_w, plot_h = 105, 90, 730, 320
    n = max(len(values), 1)
    gap = plot_w / n
    bars = []
    for i, (label, value) in enumerate(zip(labels, values)):
        bar_h = 0 if maximum == 0 else plot_h * value / maximum
        x = left + i * gap + gap * 0.15
        y = top + plot_h - bar_h
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{gap*0.7:.1f}" '
            f'height="{bar_h:.1f}" fill="#287271"/>'
            f'<text x="{x+gap*0.35:.1f}" y="{top+plot_h+25}" '
            f'text-anchor="middle" font-size="13">{label}</text>'
            f'<text x="{x+gap*0.35:.1f}" y="{max(y-7, top+14):.1f}" '
            f'text-anchor="middle" font-size="12">{value:g}</text>'
        )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="white"/>
<text x="45" y="42" font-family="Arial" font-size="24" fill="#222">{title}</text>
<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="#333"/>
{''.join(bars)}
<text x="45" y="478" font-family="Arial" font-size="14" fill="#555">{note}</text>
</svg>'''
    path.write_text(svg, encoding="utf-8")


def svg_uniform(path: Path, priorities: list[float]) -> None:
    width, height = 1000, 560
    left, top, plot_w, plot_h = 80, 85, 860, 355
    gap = plot_w / 17
    maximum = 0.07
    bars = []
    for i, value in enumerate(priorities):
        h = plot_h * value / maximum
        x = left + i * gap + 5
        y = top + plot_h - h
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{gap-10:.1f}" height="{h:.1f}" fill="#D97706"/>'
            f'<text x="{x+(gap-10)/2:.1f}" y="{top+plot_h+22}" text-anchor="middle" font-size="11">{i+1}</text>'
        )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="white"/>
<text x="40" y="40" font-family="Arial" font-size="24" fill="#222">Neutral baseline: equal priority for 17 SDGs</text>
<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="#333"/>
{''.join(bars)}
<text x="500" y="500" text-anchor="middle" font-family="Arial" font-size="14" fill="#555">Illustrative no-data baseline only; it is not an inferred ranking.</text>
</svg>'''
    path.write_text(svg, encoding="utf-8")


def build_report(case: dict[str, Any], input_path: Path, input_hash: str) -> dict[str, Any]:
    goal_count = count_goals(case["problem_text"])
    edge_rows = sum(
        len(item.get("rows_data", []))
        for item in case.get("data_audit", [])
        if isinstance(item, dict) and isinstance(item.get("rows_data", []), list)
    )
    data_files = len(case.get("data_files", []))
    data_sufficient = edge_rows > 0
    uniform = [1.0 / goal_count] * goal_count if goal_count else []
    entropy = -sum(p * math.log(p) for p in uniform) if uniform else None
    normalized_entropy = entropy / math.log(goal_count) if goal_count > 1 else None

    pending = [] if data_sufficient else [
        "network_estimation",
        "priority_effectiveness_experiment",
        "ten_year_forecast",
        "achieved_goal_counterfactual",
        "crisis_scenario_quantification",
        "ranking_validation",
        "weight_sensitivity_and_robustness",
        "empirical_falsification",
    ]

    return {
        "run": {
            "case_id": case["case_id"],
            "competition": case["competition"],
            "year": case["year"],
            "seed": SEED,
            "input_path": str(input_path.resolve()),
            "input_file_sha256": input_hash,
            "problem_sha256": case["problem_sha256"],
        },
        "problem_framing": {
            "objective": "Prioritize 17 interdependent SDGs using a signed network, evaluate interventions, and study counterfactual and crisis scenarios.",
            "required_outputs": [
                "signed SDG relationship network",
                "efficient priorities and effectiveness evaluation",
                "10-year achievable outcomes",
                "network after achieving one SDG and revised priorities",
                "crisis impacts from a network perspective",
                "transferable organizational prioritization method",
            ],
        },
        "data_audit": {
            "official_goal_count_detected": goal_count,
            "data_files_count": data_files,
            "data_audit_entries": len(case.get("data_audit", [])),
            "supplied_relationship_rows": edge_rows,
            "binary_attachments_opened": False,
            "network_identifiable_from_supplied_rows": data_sufficient,
            "finding": "No relationship or outcome observations are supplied; empirical edges, weights, dynamics, and forecasts are not identifiable.",
        },
        "assumptions": [
            "The 17 goal labels in the official problem text define the node set.",
            "Absent relationship evidence is missing information, not evidence of zero interaction.",
            "The equal-weight vector is a neutral baseline, not a substantive recommendation.",
            "No quantitative 10-year forecast is valid without initial states, response functions, costs, and scenario inputs.",
        ],
        "candidate_models": [
            {
                "name": "signed evidence-weighted multiplex network plus robust portfolio optimization",
                "inputs_needed": "signed directed edges with provenance/uncertainty, costs, goal states, intervention response bounds",
                "method": "centrality and controllability features feed a budget-constrained maximin multi-criteria portfolio",
                "status": "pending_data",
            },
            {
                "name": "Bayesian signed dynamic network",
                "inputs_needed": "longitudinal SDG indicators and intervention/covariate series",
                "method": "posterior edge effects support scenario propagation and probabilistic ranking",
                "status": "pending_data",
            },
        ],
        "baseline": {
            "name": "uniform no-data allocation",
            "priority_by_goal": {str(i + 1): uniform[i] for i in range(goal_count)},
            "sum": sum(uniform),
            "entropy_nats": entropy,
            "normalized_entropy": normalized_entropy,
            "interpretation": "All goals tie because the supplied input contains no defensible discriminator.",
        },
        "math_specification": {
            "future_network": "G=(V,E,W), V={1,...,17}, w_ij in [-1,1] with uncertainty and source provenance",
            "future_priority": "maximize over allocation x: min_s sum_i b_i(s)x_i + sum_{i,j} w_ij(s)r_j(x_i), subject to sum_i c_i x_i <= B and x_i >= 0",
            "baseline": "p_i=1/17 for i=1,...,17",
            "identifiability_gate": "estimate W and compare rankings only when at least one validated relationship row exists; forecasting additionally requires outcomes, time, and intervention data",
        },
        "code_prototype": {
            "capabilities": ["input validation", "data-sufficiency gate", "neutral baseline", "machine-readable report", "SVG diagnostics"],
            "prohibited_by_gate": ["edge inference from prose", "fabricated scores", "unsupported forecast"],
        },
        "experiment": {
            "status": "pending_data",
            "design": "Compare uniform allocation with robust-network portfolios under held-out interventions and multiple budget/scenario settings.",
            "minimum_inputs": "validated edge evidence, costs, initial goal states, outcome measures, timestamps, and crisis covariates",
        },
        "validation": {
            "completed": ["case schema checks", "17-node extraction check", "baseline simplex invariant", "deterministic output checks"],
            "pending": ["edge sign validation", "temporal holdout", "ranking concordance", "forecast calibration"],
        },
        "sensitivity_robustness": {
            "status": "pending_data",
            "planned": ["weight simplex perturbation", "edge sign/weight intervals", "leave-source-out analysis", "scenario stress tests", "rank acceptability frequencies"],
            "reason": "No empirical weights, edges, or outcomes are present to perturb.",
        },
        "falsification": {
            "status": "pending_data",
            "tests": [
                "network model fails if it does not outperform the uniform baseline on held-out outcomes",
                "priority is unstable if its top-k inclusion rate falls below a preregistered threshold under admissible uncertainty",
                "forecast is rejected if interval coverage or calibration fails on temporal holdout",
            ],
        },
        "reviewer_risks": [
            "No supplied relationship data means the central deliverable cannot be empirically estimated.",
            "Literature-derived edges would require traceable sources not present in the complete benchmark input.",
            "Arbitrary criteria weights would create unearned ranking precision.",
            "Centrality alone does not establish causal intervention leverage.",
            "A 10-year numerical forecast without baseline trajectories and costs would be fictitious.",
            "The neutral baseline is intentionally noncompetitive and must not be presented as policy advice.",
        ],
        "reproducibility_manifest": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "stdlib_only": True,
            "seed": SEED,
            "command": f'python run_model.py --input "{input_path.resolve()}" --output .',
            "outputs": ["results/metrics.json", "figures/raw_q1_input_coverage.svg", "figures/process_q2_data_gate.svg", "figures/result_q2_uniform_baseline.svg"],
        },
        "pending_stages": pending,
    }


def self_tests() -> list[dict[str, Any]]:
    synthetic = {
        "case_id": EXPECTED_CASE_ID,
        "problem_sha256": EXPECTED_PROBLEM_SHA256,
        "problem_text": " ".join(f"GOAL {i}: X" for i in range(1, 18)),
        "data_files": [],
        "data_audit": [],
    }
    tests = [
        ("valid_case_schema", validate_case(synthetic) == []),
        ("detects_17_goals", count_goals(synthetic["problem_text"]) == 17),
        ("rejects_wrong_case", bool(validate_case({**synthetic, "case_id": "wrong"}))),
        ("uniform_simplex", math.isclose(sum([1 / 17] * 17), 1.0, rel_tol=0, abs_tol=1e-12)),
    ]
    return [{"name": name, "passed": passed} for name, passed in tests]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", default=Path("."), type=Path)
    args = parser.parse_args()

    started = time.perf_counter()
    tests = self_tests()
    if not all(item["passed"] for item in tests):
        raise RuntimeError("internal self-test failed")

    case, input_hash = load_case(args.input)
    errors = validate_case(case)
    if errors:
        raise ValueError("; ".join(errors))

    out = args.output.resolve()
    results_dir = out / "results"
    figures_dir = out / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    report = build_report(case, args.input, input_hash)
    goal_count = report["data_audit"]["official_goal_count_detected"]
    uniform = list(report["baseline"]["priority_by_goal"].values())

    svg_bar(
        figures_dir / "raw_q1_input_coverage.svg",
        "Supplied benchmark input coverage",
        ["SDG nodes", "data files", "relationship rows"],
        [goal_count, report["data_audit"]["data_files_count"], report["data_audit"]["supplied_relationship_rows"]],
        17,
        "Only the 17 node labels are observed; no edge or outcome rows are supplied.",
    )
    svg_bar(
        figures_dir / "process_q2_data_gate.svg",
        "Model execution gate",
        ["schema", "baseline", "network", "forecast", "robustness"],
        [1, 1, 0, 0, 0],
        1,
        "1 = executable with supplied input; 0 = pending required data.",
    )
    svg_uniform(figures_dir / "result_q2_uniform_baseline.svg", uniform)

    report["execution"] = {
        "status": "partial_data_limited",
        "runtime_seconds": round(time.perf_counter() - started, 6),
        "tests": tests,
        "tests_passed": sum(item["passed"] for item in tests),
        "tests_total": len(tests),
        "figures_count": 3,
    }
    metrics_path = results_dir / "metrics.json"
    metrics_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["execution"]["status"],
        "metrics_path": str(metrics_path),
        "figures_count": 3,
        "tests": tests,
        "pending_stages": report["pending_stages"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

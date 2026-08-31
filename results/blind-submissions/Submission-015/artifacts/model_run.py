"""Deterministic, data-honest scaffold for ICM 2023 Problem D.

The supplied benchmark contains the official prompt but no empirical relationship
rows. This runner records a complete model contract without manufacturing edges,
weights, priorities, forecasts, or validation scores.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
from pathlib import Path
from typing import Any


EXPECTED_CASE_ID = "icm-2023-d"
REQUIRED_SECTIONS = [
    "problem_framing",
    "data_audit",
    "assumptions",
    "candidate_models",
    "baseline",
    "math_specification",
    "code_prototype",
    "experiment",
    "validation",
    "sensitivity_robustness",
    "falsification",
    "reviewer_risks",
    "reproducibility_manifest",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_case(path: Path) -> dict[str, Any]:
    case = json.loads(path.read_text(encoding="utf-8"))
    if case.get("case_id") != EXPECTED_CASE_ID:
        raise ValueError(f"expected case_id {EXPECTED_CASE_ID!r}")
    return case


def extract_goals(problem_text: str) -> list[dict[str, Any]]:
    matches = re.findall(
        r"GOAL\s+(\d+):\s*(.*?)\s*(?=GOAL\s+\d+:|Your PDF solution)",
        problem_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    goals = [
        {"id": int(number), "name": " ".join(name.split())}
        for number, name in matches
    ]
    if [goal["id"] for goal in goals] != list(range(1, 18)):
        raise ValueError("official prompt did not yield exactly SDGs 1 through 17")
    return goals


def build_report(case: dict[str, Any]) -> dict[str, Any]:
    goals = extract_goals(case["problem_text"])
    no_rows = not case.get("data_audit") and not case.get("data_files")
    pending_reason = (
        "The benchmark supplies no relationship, intervention, cost, outcome, "
        "time-series, or crisis-scenario observations."
    )
    report: dict[str, Any] = {
        "problem_framing": {
            "case_id": case["case_id"],
            "objective": (
                "Represent signed interdependence among 17 SDGs and prioritize "
                "interventions for efficient UN progress under constraints."
            ),
            "required_decisions": [
                "construct the SDG relationship network",
                "select and evaluate priorities",
                "estimate reasonable 10-year outcomes",
                "analyze the network after one SDG is achieved",
                "assess international-crisis effects",
                "explain transfer to other organizations",
            ],
            "decision_unit": "one of the 17 official Sustainable Development Goals",
            "status": "model_contract_complete_empirical_solution_pending",
        },
        "data_audit": {
            "source_status": case.get("source_status"),
            "problem_sha256": case.get("problem_sha256"),
            "declared_data_sha256": case.get("data_sha256"),
            "official_goals_found": len(goals),
            "goals": goals,
            "data_files_count": len(case.get("data_files", [])),
            "audited_tables_count": len(case.get("data_audit", [])),
            "rows_available": 0 if no_rows else None,
            "usable_relationship_edges": 0 if no_rows else None,
            "fields_required_but_absent": [
                "directed SDG source and target",
                "interaction sign and magnitude",
                "evidence strength or uncertainty",
                "intervention cost or budget",
                "baseline progress and outcome response",
                "time index for 10-year calibration",
                "crisis exposure or shock magnitude",
            ],
            "limitation": pending_reason,
        },
        "assumptions": {
            "structural": [
                "The 17 official SDGs are the complete node set for the base model.",
                "Relationships should be directed and signed because effects may differ by direction and may be beneficial or harmful.",
                "A zero weight may be used only for an observed or justified absence, never as a substitute for missing evidence.",
            ],
            "estimation": [
                "Edge weights, criterion weights, budgets, and response rates are not identifiable from the supplied benchmark.",
                "No independence, stationarity, linearity, or equal-cost assumption is asserted without data.",
            ],
        },
        "candidate_models": [
            {
                "name": "signed_directed_network_plus_robust_mcda",
                "role": "primary",
                "description": (
                    "Estimate a signed weighted adjacency matrix, derive network leverage and vulnerability criteria, "
                    "then rank interventions across an explicit uncertainty set of normalized criterion weights."
                ),
                "required_inputs": ["edge evidence", "criterion definitions", "criterion weights or admissible ranges", "costs"],
                "status": "specified_not_estimable",
            },
            {
                "name": "constrained_dynamic_influence_simulation",
                "role": "forecast_and_counterfactual",
                "description": (
                    "Propagate bounded goal-progress states through the signed network under an intervention budget, "
                    "then remove or clamp an achieved goal and repeat under crisis shocks."
                ),
                "required_inputs": ["initial progress", "response rates", "intervention effects", "shock scenarios", "calibration targets"],
                "status": "specified_not_estimable",
            },
        ],
        "baseline": {
            "name": "data-honest_unranked_baseline",
            "rule": "Keep every official SDG in its source order and assign no score when distinguishing evidence is absent.",
            "ranking_status": "pending",
            "goals": [{**goal, "priority_score": None, "rank": None} for goal in goals],
            "reason": pending_reason,
        },
        "math_specification": {
            "network": {
                "nodes": "V={1,...,17}",
                "adjacency": "A=[a_ij], where a_ij in [-1,1] is the evidenced signed effect of SDG i on SDG j",
                "evidence_rule": "a_ij is missing until supported; missing is not numerically zero",
            },
            "priority_model": {
                "criteria": "x_ik=(benefit leverage, harm risk reduction, feasibility, equity gain, robustness, cost efficiency)",
                "normalization": "z_ik=(x_ik-min_i x_ik)/(max_i x_ik-min_i x_ik), with direction reversed for cost criteria",
                "score": "S_i(w)=sum_k w_k z_ik, w_k>=0, sum_k w_k=1",
                "robustness": "R_i=P_w(i is in top K) over a declared weight uncertainty set W",
                "optimization": "maximize sum_i S_i(w)y_i subject to sum_i c_i y_i<=B and y_i in {0,1}",
            },
            "dynamics": {
                "state": "p(t) in [0,1]^17",
                "update": "p(t+1)=clip(p(t)+D[u(t)+A^T p(t)+s(t)],0,1)",
                "achieved_goal_counterfactual": "clamp p_g(t)=1 and compare the induced subnetwork or retained influence paths",
                "ten_year_effectiveness": "Delta=sum_i q_i[p_i(10)-p_i(0)] with uncertainty intervals from calibrated parameter draws",
            },
            "identifiability_status": "pending_missing_empirical_inputs",
        },
        "code_prototype": {
            "status": "executed_audit_scaffold",
            "capabilities": [
                "validate the benchmark identity and 17-goal ontology",
                "preserve missing values rather than impute edges or scores",
                "emit report, metrics, manifest, and audit SVGs deterministically",
            ],
            "excluded": ["edge inference", "priority scoring", "forecast simulation"],
        },
        "experiment": {
            "status": "pending",
            "design": [
                "Fit or elicit signed edges with source-level uncertainty.",
                "Compare the robust-MCDA ranking against centrality-only and equal-weight baselines.",
                "Backtest held-out goal-progress changes where time-indexed observations exist.",
                "Run achieved-goal and crisis counterfactuals over calibrated uncertainty draws.",
            ],
            "blocking_reason": pending_reason,
        },
        "validation": {
            "status": "partial_input_contract_only",
            "completed_checks": [
                "case identity matches icm-2023-d",
                "official SDG identifiers are exactly 1 through 17",
                "empty data inventory is propagated to null scores and pending empirical stages",
            ],
            "pending_checks": [
                "edge sign and magnitude validation",
                "out-of-sample ranking validation",
                "forecast calibration and coverage",
                "budget-feasibility validation",
            ],
        },
        "sensitivity_robustness": {
            "status": "pending",
            "planned_analyses": [
                "simplex or Dirichlet sampling over criterion weights",
                "edge deletion and sign-flip perturbations weighted by evidence confidence",
                "budget and intervention-effect sweeps",
                "rank acceptability, top-K inclusion frequency, and Kendall rank stability",
            ],
            "blocking_reason": pending_reason,
        },
        "falsification": {
            "status": "pending",
            "tests": [
                "reject a claimed positive edge if its uncertainty interval is not directionally stable",
                "reject a priority if it loses top-K membership under small admissible weight changes",
                "reject the dynamic model if it cannot outperform a persistence forecast out of sample",
                "reject transferability if criterion directions or constraints fail in a target organization",
            ],
            "blocking_reason": pending_reason,
        },
        "reviewer_risks": [
            {"risk": "arbitrary relationship weights", "mitigation": "require traceable edge evidence and uncertainty", "current_status": "unresolved_no_data"},
            {"risk": "scale mismatch across criteria", "mitigation": "predeclare directions and normalization; audit degenerate ranges", "current_status": "specified"},
            {"risk": "unstable rankings", "mitigation": "report rank acceptability rather than one weight vector", "current_status": "pending"},
            {"risk": "causal overclaiming from a descriptive network", "mitigation": "separate association, expert elicitation, and causal evidence", "current_status": "specified"},
            {"risk": "unsupported 10-year forecasts", "mitigation": "calibrate and backtest dynamics before forecasting", "current_status": "pending"},
            {"risk": "crisis scenarios chosen after seeing results", "mitigation": "predeclare shock definitions and parameter ranges", "current_status": "pending"},
        ],
        "reproducibility_manifest": {},
    }
    if list(report) != REQUIRED_SECTIONS:
        raise AssertionError("report section contract changed")
    return report


def _svg(title: str, lines: list[str], bars: list[tuple[str, int, str]]) -> str:
    width, height = 1000, 620
    escaped = lambda value: (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="55" y="58" font-family="Arial" font-size="27" fill="#151515">{escaped(title)}</text>',
    ]
    for index, line in enumerate(lines):
        parts.append(f'<text x="55" y="{92 + 23 * index}" font-family="Arial" font-size="16" fill="#444444">{escaped(line)}</text>')
    start_y = 160
    for index, (label, value, color) in enumerate(bars):
        y = start_y + index * 38
        bar_width = max(2, min(800, value * 42))
        parts.extend([
            f'<text x="55" y="{y + 18}" font-family="Arial" font-size="15" fill="#222222">{escaped(label)}</text>',
            f'<rect x="310" y="{y}" width="{bar_width}" height="24" fill="{color}"/>',
            f'<text x="{322 + bar_width}" y="{y + 18}" font-family="Arial" font-size="15" fill="#222222">{value}</text>',
        ])
    parts.append('</svg>')
    return "\n".join(parts)


def write_figures(output_dir: Path) -> list[Path]:
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        (
            "raw_q1_input_inventory.svg",
            "Input inventory",
            ["Counts are read directly from the deterministic case summary."],
            [("Official SDG nodes", 17, "#2f6f4e"), ("Data files", 0, "#b23a48"), ("Audited tables", 0, "#b23a48"), ("Relationship rows", 0, "#b23a48")],
        ),
        (
            "process_q1_estimation_gates.svg",
            "Estimation gate status",
            ["A value of 1 means the gate is satisfied; 0 means pending."],
            [("Goal ontology", 1, "#2f6f4e"), ("Edge evidence", 0, "#b23a48"), ("Cost evidence", 0, "#b23a48"), ("Time-series calibration", 0, "#b23a48")],
        ),
        (
            "result_q1_output_status.svg",
            "Output status",
            ["No empirical result is promoted beyond the available evidence."],
            [("Model contract", 1, "#2f6f4e"), ("Priority ranking", 0, "#b23a48"), ("10-year forecast", 0, "#b23a48"), ("Crisis effects", 0, "#b23a48")],
        ),
    ]
    paths = []
    for filename, title, lines, bars in specs:
        path = figure_dir / filename
        path.write_text(_svg(title, lines, bars), encoding="utf-8", newline="\n")
        paths.append(path)
    return paths


def run(case_path: Path, output_dir: Path) -> dict[str, Any]:
    case_path = case_path.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    case = load_case(case_path)
    report = build_report(case)
    figures = write_figures(output_dir)
    pending = [
        "network_edge_estimation",
        "priority_ranking",
        "ten_year_forecast",
        "achieved_goal_counterfactual",
        "crisis_impact_quantification",
        "external_validation",
        "sensitivity_robustness",
        "empirical_falsification",
    ]
    metrics = {
        "case_id": case["case_id"],
        "official_goals": 17,
        "data_files": len(case.get("data_files", [])),
        "audited_tables": len(case.get("data_audit", [])),
        "rows_available": 0,
        "relationship_edges_available": 0,
        "priority_ranking_computed": False,
        "forecast_computed": False,
        "figures_count": len(figures),
        "pending_stages_count": len(pending),
        "scores": None,
    }
    command = f'python "{Path(__file__).resolve()}" --case "{case_path}" --output "{output_dir}"'
    manifest = {
        "case_id": case["case_id"],
        "random_seed": None,
        "randomness_used": False,
        "input": {"path": str(case_path), "sha256": sha256_file(case_path)},
        "runtime": {"python": platform.python_version(), "implementation": platform.python_implementation()},
        "dependencies": {"python_standard_library_only": True},
        "parameters": {"expected_case_id": EXPECTED_CASE_ID, "missing_value_policy": "preserve_as_null"},
        "reproduction_command": command,
    }
    report["reproducibility_manifest"] = manifest
    report_path = output_dir / "modeling_report.json"
    metrics_path = output_dir / "metrics.json"
    manifest_path = output_dir / "reproducibility_manifest.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {
        "status": "partial",
        "code_path": str(Path(__file__).resolve()),
        "metrics_path": str(metrics_path),
        "figures_count": len(figures),
        "tests": "not_run_by_model_command",
        "pending_stages": pending,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.case, args.output), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

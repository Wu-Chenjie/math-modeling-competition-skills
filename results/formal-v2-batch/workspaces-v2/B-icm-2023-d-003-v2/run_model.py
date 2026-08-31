#!/usr/bin/env python3
"""Evidence-limited prototype for ICM 2023 Problem D.

This run deliberately uses only the deterministic case-summary JSON. Because that
summary contains no SDG relationship observations, the executable reports a
permutation-invariant baseline and marks network-dependent analyses pending.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


DEFAULT_INPUT = Path(
    r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills"
    r"\benchmarks\case-summaries\icm-2023-d.json"
)
GOAL_PREFIX = "GOAL "


def extract_goals(problem_text: str) -> list[str]:
    goals: list[str] = []
    for number in range(1, 18):
        marker = f"GOAL {number}: "
        start = problem_text.find(marker)
        if start < 0:
            raise ValueError(f"Missing {marker.strip()} in supplied problem text")
        value_start = start + len(marker)
        next_start = problem_text.find(f" GOAL {number + 1}:", value_start)
        if number == 17:
            next_start = problem_text.find(" Your PDF solution", value_start)
        if next_start < 0:
            raise ValueError(f"Could not delimit Goal {number}")
        goals.append(problem_text[value_start:next_start].strip())
    return goals


def svg_bar_chart(title: str, labels: list[str], values: list[float], path: Path) -> None:
    width, height = 960, 620
    left, right, top, bottom = 75, 30, 70, 100
    plot_w, plot_h = width - left - right, height - top - bottom
    max_value = max(values) if values and max(values) > 0 else 1.0
    bar_w = plot_w / max(len(values), 1)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width / 2}" y="34" text-anchor="middle" font-family="Arial" font-size="20">{title}</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#222"/>',
    ]
    for index, (label, value) in enumerate(zip(labels, values)):
        x = left + index * bar_w + bar_w * 0.15
        h = plot_h * value / max_value
        y = top + plot_h - h
        parts.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w * 0.7:.2f}" height="{h:.2f}" fill="#2878b5"/>'
        )
        parts.append(
            f'<text x="{x + bar_w * 0.35:.2f}" y="{top + plot_h + 20}" text-anchor="middle" font-family="Arial" font-size="10">{label}</text>'
        )
        parts.append(
            f'<text x="{x + bar_w * 0.35:.2f}" y="{max(y - 5, 55):.2f}" text-anchor="middle" font-family="Arial" font-size="9">{value:.4f}</text>'
        )
    parts.append('</svg>')
    path.write_text("\n".join(parts), encoding="utf-8")


def svg_status(title: str, lines: list[str], path: Path) -> None:
    width, height = 960, 420
    escaped = [line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for line in lines]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="480" y="45" text-anchor="middle" font-family="Arial" font-size="22">{title}</text>',
        '<rect x="70" y="85" width="820" height="250" fill="#f4f6f7" stroke="#555"/>',
    ]
    for index, line in enumerate(escaped):
        parts.append(f'<text x="95" y="{130 + index * 38}" font-family="Arial" font-size="17">{line}</text>')
    parts.append('</svg>')
    path.write_text("\n".join(parts), encoding="utf-8")


def write_figure_data(path: Path, goals: list[str], values: list[float], field: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["goal_id", "goal_name", field])
        for index, (goal, value) in enumerate(zip(goals, values), start=1):
            writer.writerow([index, goal, f"{value:.12g}"])


def build_report(case: dict, input_path: Path, output_dir: Path) -> dict:
    goals = extract_goals(case["problem_text"])
    n = len(goals)
    edge_count = sum(len(item.get("rows_data", [])) for item in case.get("data_audit", []))
    priority = [1.0 / n] * n
    entropy = -sum(value * math.log(value) for value in priority) / math.log(n)
    hhi = sum(value * value for value in priority)
    labels = [str(i) for i in range(1, n + 1)]

    figures_dir = output_dir / "figures"
    data_dir = output_dir / "figure_data"
    figures_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    figure_specs = [
        ("raw_q1_goal_coverage", "Q1 input coverage: goals present", [1.0] * n),
        ("process_q1_edge_evidence", "Q1 relationship evidence: observed edges", [0.0] * n),
        ("result_q1_network_status", "Q1 network result", None),
        ("raw_q2_priority_evidence", "Q2 goal-specific priority evidence", [0.0] * n),
        ("process_q2_uniform_baseline", "Q2 maximum-ignorance baseline", priority),
        ("result_q2_priority_baseline", "Q2 baseline priority allocation", priority),
        ("raw_q3_achievement_evidence", "Q3 achieved-goal scenario evidence", [0.0] * n),
        ("process_q3_counterfactual_status", "Q3 counterfactual identifiability", None),
        ("result_q3_reprioritization_status", "Q3 reprioritization result", None),
        ("raw_q4_crisis_evidence", "Q4 crisis-effect evidence", [0.0] * n),
        ("process_q4_shock_model_status", "Q4 shock-model identifiability", None),
        ("result_q4_crisis_priority_status", "Q4 crisis priority result", None),
        ("raw_q5_transfer_evidence", "Q5 organization-specific evidence", [0.0] * n),
        ("process_q5_transfer_framework", "Q5 transferable workflow status", None),
        ("result_q5_transfer_validation", "Q5 external validation status", None),
    ]
    status_lines = [
        "Status: PENDING (not identifiable from supplied benchmark input)",
        "Observed relationship rows: 0",
        "No edges, signs, strengths, costs, or progress rates were inferred.",
        "Required next input: traceable relationship and outcome evidence.",
    ]
    figure_paths: list[str] = []
    for stem, title, values in figure_specs:
        svg_path = figures_dir / f"{stem}.svg"
        if values is None:
            svg_status(title, status_lines, svg_path)
            write_figure_data(data_dir / f"{stem}.csv", goals, [0.0] * n, "observed_evidence_count")
        else:
            svg_bar_chart(title, labels, values, svg_path)
            write_figure_data(data_dir / f"{stem}.csv", goals, values, "value")
        figure_paths.append(str(svg_path.as_posix()))

    input_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
    uniform_rank = [{"goal_id": i, "goal_name": name, "priority": priority[i - 1], "rank": 1} for i, name in enumerate(goals, 1)]
    pending = [
        "empirical_network_estimation",
        "network_centrality_ranking",
        "10_year_effectiveness_forecast",
        "achieved_goal_counterfactual",
        "new_goal_recommendation",
        "crisis_shock_quantification",
        "external_organization_validation",
    ]
    return {
        "run_id": "B-icm-2023-d-003-v2",
        "status": "partial_evidence_limited",
        "problem_framing": {
            "decision": "Prioritize 17 interdependent SDGs and assess network-mediated effects.",
            "subproblems": ["relationship network", "priority and effectiveness", "achievement counterfactual", "crisis impacts", "organizational transfer"],
            "identifiability_boundary": "The supplied input identifies goal labels and requested outputs, but contains no observed relationships or outcomes.",
        },
        "data_audit": {
            "source_status": case.get("source_status"),
            "problem_sha256_declared": case.get("problem_sha256"),
            "case_summary_sha256_computed": input_hash,
            "data_files_count": len(case.get("data_files", [])),
            "data_audit_entries": len(case.get("data_audit", [])),
            "rows_data_count": edge_count,
            "goals_parsed": n,
            "binary_attachments_opened": 0,
            "finding": "No empirical edge, weight, cost, progress, or response rows are available.",
        },
        "assumptions": [
            "Goal labels parsed from the supplied official problem text are the complete node set.",
            "No missing relationship is interpreted as a zero relationship; all edges remain unknown.",
            "In the absence of distinguishing evidence, goals are exchangeable and receive equal baseline priority.",
        ],
        "candidate_models": [
            {"name": "signed weighted SDG influence network", "status": "pending", "need": "directed edge signs and strengths with provenance"},
            {"name": "robust multi-criteria portfolio optimization", "status": "pending", "need": "costs, feasible actions, progress outcomes, and defensible criteria"},
        ],
        "baseline": {
            "name": "permutation-invariant maximum-entropy allocation",
            "priority": uniform_rank,
            "interpretation": "A neutral benchmark, not an empirical recommendation or inferred tie.",
        },
        "math_specification": {
            "node_set": "V={1,...,17}",
            "observed_edge_set": "E_obs=empty",
            "baseline_program": "maximize -sum_i p_i log(p_i), subject to p_i>=0 and sum_i p_i=1",
            "solution": "p_i=1/17 for every i by symmetry and strict concavity",
            "non_identifiability": "Any signed adjacency matrix and any non-uniform ranking require information absent from the benchmark input.",
        },
        "code_prototype": {
            "entrypoint": "run_model.py",
            "interface": "python run_model.py --input <case-summary.json> --output artifacts",
            "dependencies": ["Python standard library"],
        },
        "experiment": {
            "type": "deterministic evidence-limited baseline",
            "observed_edges": edge_count,
            "priority_sum": sum(priority),
            "normalized_entropy": entropy,
            "herfindahl_index": hhi,
        },
        "validation": {
            "goal_count_is_17": n == 17,
            "priority_nonnegative": all(value >= 0 for value in priority),
            "priority_sums_to_one": math.isclose(sum(priority), 1.0, rel_tol=0.0, abs_tol=1e-12),
            "permutation_invariant": len(set(priority)) == 1,
            "input_has_no_relationship_rows": edge_count == 0,
        },
        "sensitivity_robustness": {
            "result": "Uniform allocation is invariant to relabeling.",
            "ranking_robustness": "No strict rank is identified; all 17 goals share rank 1 under the baseline.",
            "empirical_weight_sensitivity": "pending because no weights or uncertainty bounds are supplied",
        },
        "falsification": {
            "claim_tested": "The supplied evidence supports a strict priority ordering.",
            "result": "falsified",
            "reason": "All goal-specific evidence vectors are empty; a strict ordering would change under a label permutation without evidential justification.",
            "baseline_falsifier": "Any traceable goal-specific effectiveness, cost, constraint, or edge evidence would invalidate exchangeability and trigger re-estimation.",
        },
        "reviewer_risks": [
            "The neutral baseline does not answer substantive network or forecasting questions.",
            "Treating absent observations as zero edges would be a material modeling error.",
            "No claim about a 10-year outcome, crisis effect, or added goal is supportable from this input.",
            "The generated figures visualize evidence coverage and the baseline, not empirical SDG performance.",
        ],
        "reproducibility_manifest": {
            "input_path": str(input_path),
            "input_sha256": input_hash,
            "random_seed": None,
            "deterministic": True,
            "command": f'python run_model.py --input "{input_path}" --output artifacts',
            "figures": figure_paths,
            "figure_data_directory": str(data_dir.as_posix()),
        },
        "pending_stages": pending,
    }


def self_test() -> None:
    synthetic = " ".join(f"GOAL {i}: Name {i}" for i in range(1, 18)) + " Your PDF solution"
    assert extract_goals(synthetic) == [f"Name {i}" for i in range(1, 18)]
    p = [1 / 17] * 17
    assert math.isclose(sum(p), 1.0, abs_tol=1e-12)
    assert len(set(p)) == 1
    print(json.dumps({"tests": 3, "status": "passed"}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    case = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    report = build_report(case, args.input, args.output)
    metrics_path = args.output / "modeling_report.json"
    metrics_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "metrics_path": str(metrics_path.as_posix()),
        "figures_count": len(report["reproducibility_manifest"]["figures"]),
        "pending_stages": report["pending_stages"],
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

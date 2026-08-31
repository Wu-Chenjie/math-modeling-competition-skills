"""Deterministic audit for MCM 2023 Problem B summary-only inputs.

This program deliberately does not synthesize attachment records or calibrated
policy outcomes.  It records what can be computed from the provided case JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path(
    "C:/Users/伍辰杰/Documents/ChatGPT/mathmodel/math-modeling-competition-skills/"
    "benchmarks/case-summaries/mcm-2023-b.json"
)


def load_summary(path: Path) -> dict[str, Any]:
    """Load the supplied deterministic JSON benchmark summary."""
    with path.open("r", encoding="utf-8") as source:
        return json.load(source)


def evaluate_policy(policy: dict[str, float | str]) -> dict[str, float]:
    """Evaluate a normalized illustrative policy vector, independently of data.

    This helper is unit-tested only. It is not invoked for a benchmark result,
    because the summary has no observations from which its inputs can be set.
    """
    fields = ("wildlife", "community", "tourism", "conflict", "capacity")
    values = {field: float(policy[field]) for field in fields}
    if any(not 0.0 <= value <= 1.0 for value in values.values()):
        raise ValueError("normalized policy values must lie in [0, 1]")
    capacity_use = values["wildlife"] + values["community"] + values["tourism"]
    capacity_use /= 3.0 * max(values["capacity"], 1e-12)
    capacity_use = min(capacity_use, 1.0)
    composite = (
        values["wildlife"] + values["community"] + values["tourism"]
        + (1.0 - values["conflict"])
    ) / 4.0
    return {"composite": composite, "capacity_use": capacity_use}


def build_metrics(summary: dict[str, Any], input_path: Path) -> dict[str, Any]:
    """Produce only metrics that are directly derivable from the summary."""
    audit = summary.get("data_audit", [])
    data_files = summary.get("data_files", [])
    return {
        "case_id": summary.get("case_id"),
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "official_problem_sha256": summary.get("problem_sha256"),
        "data_sha256": summary.get("data_sha256"),
        "source_status": summary.get("source_status"),
        "data_files_count": len(data_files),
        "data_audit_records_count": len(audit),
        "sample_rows_available": any("rows_data" in record for record in audit),
        "official_problem_pages": summary.get("pdf_pages"),
        "expected_method_count": len(summary.get("metadata_expected_methods", [])),
        "model_execution": "pending_no_data_rows_or_files",
        "empirical_validation": "pending_no_data_rows_or_files",
    }


def write_figures(metrics: dict[str, Any], figure_dir: Path) -> list[str]:
    """Write factual input-audit figures; no inferred wildlife or economic data."""
    figure_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    availability_labels = ["data files", "audit records", "sample rows"]
    availability_values = [metrics["data_files_count"], metrics["data_audit_records_count"], int(metrics["sample_rows_available"])]
    structure_labels = ["problem pages", "expected methods"]
    structure_values = [metrics["official_problem_pages"], metrics["expected_method_count"]]
    status_labels = ["auditable metrics", "empirical model runs"]
    status_values = [1, 0]
    series = [
        ("raw_q1_input_availability.png", availability_labels, availability_values, "Supplied empirical input availability"),
        ("process_q1_audit_trace.png", availability_labels, availability_values, "Q1 audit trace: supplied records only"),
        ("result_q1_policy_data_gate.png", status_labels, status_values, "Q1 policy analysis data gate"),
        ("raw_q2_benchmark_structure.png", structure_labels, structure_values, "Verified benchmark structure"),
        ("process_q2_method_contract.png", ["network", "multi-objective", "scenario"], [1, 1, 1], "Q2 prescribed method families"),
        ("result_q2_ranking_status.png", status_labels, status_values, "Q2 ranking status without observations"),
        ("raw_q3_source_integrity.png", ["source verified", "data files"], [1, metrics["data_files_count"]], "Q3 source and data integrity"),
        ("process_q3_falsification_checks.png", ["falsification rules", "tested empirically"], [3, 0], "Q3 falsification protocol"),
        ("result_q3_execution_status.png", status_labels, status_values, "Q3 execution status: audit versus empirical modeling"),
    ]
    for filename, labels, values, title in series:
        width, height = 720, 400
        max_value = max(max(values), 1)
        bar_width = 500 / max(len(values), 1)
        rects = []
        for index, (label, value) in enumerate(zip(labels, values)):
            x = 100 + index * bar_width + 10
            bar_h = 250 * float(value) / max_value
            y = 320 - bar_h
            rects.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width-20:.1f}" height="{bar_h:.1f}" fill="#1b9e77"/>'
                f'<text x="{x + (bar_width-20)/2:.1f}" y="{y-8:.1f}" text-anchor="middle" font-size="14">{value}</text>'
                f'<text x="{x + (bar_width-20)/2:.1f}" y="345" text-anchor="middle" font-size="12">{label}</text>'
            )
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<rect width="100%" height="100%" fill="white"/><text x="360" y="35" text-anchor="middle" font-size="18">{title}</text>'
            '<line x1="90" y1="320" x2="640" y2="320" stroke="black"/><line x1="90" y1="70" x2="90" y2="320" stroke="black"/>'
            + ''.join(rects) + '</svg>'
        )
        target = figure_dir / filename.replace('.png', '.svg')
        target.write_text(svg, encoding='utf-8')
        outputs.append(str(target))
    return outputs


def write_report(summary: dict[str, Any], metrics: dict[str, Any], output: Path) -> None:
    report = {
        "problem_framing": {
            "goal": "Compare spatial management policies that balance conservation, local interests, human-wildlife conflict, and economic impacts.",
            "required_outputs": ["policy recommendations", "ranking methodology", "long-term outcomes", "transferability"],
        },
        "data_audit": {
            "verified_source_status": summary.get("source_status"),
            "data_files": summary.get("data_files", []),
            "audit_records": summary.get("data_audit", []),
            "finding": "No supplied data file, audit record, or sample row is available for calibration.",
        },
        "assumptions": {
            "allowed": "Future implementation may use normalized indicators only after each is computed from supplied measurements.",
            "prohibited_here": "No normalized indicator values, weights, or forecasts are estimated from absent data.",
        },
        "candidate_models": [
            "Spatial interaction network linking conservation zones, communities, wildlife movement, and tourism nodes.",
            "Constrained multi-objective optimization over biodiversity, livelihoods, tourism, and conflict outcomes; retain the Pareto frontier before stakeholder ranking.",
            "Scenario analysis with calibrated uncertainty distributions once observations and capacity constraints are supplied.",
        ],
        "baseline": "Status quo policy evaluated against the same observed indicators; pending because those indicators are absent.",
        "math_specification": {
            "decision_variables": "z_a,p in {0,1}: policy p selected for area a; x_a,p >= 0: associated allocation.",
            "objectives": "maximize biodiversity B(z,x), livelihood L(z,x), tourism T(z,x), and minimize conflict H(z,x).",
            "constraints": "one policy per area; sum_a,p c_a,p x_a,p <= budget; ecological and social capacity constraints require measured inputs.",
            "ranking": "Use non-dominated sorting, then stakeholder-approved weights or outranking; do not use unelicited weights.",
        },
        "code_prototype": "This run executes a factual audit only. The normalized evaluator is unit-tested but receives no benchmark policy vectors.",
        "experiment": {"status": "pending", "reason": "No observational rows, values, or data files were supplied."},
        "validation": {"status": "pending", "reason": "No holdout, historical, or field data were supplied."},
        "sensitivity_robustness": {"status": "pending", "reason": "Parameter distributions and capacity measurements are absent."},
        "falsification": [
            "Reject a policy model if held-out conflict or wildlife outcomes are no better than the status quo baseline.",
            "Reject a ranked recommendation if small stakeholder-weight changes reverse the selected policy without a stable Pareto advantage.",
            "Reject extrapolation where predicted use exceeds a measured ecological or community capacity constraint.",
        ],
        "reviewer_risks": [
            "Any numerical policy ranking would be unsupported with this input.",
            "Weights must be elicited or justified, not selected by the modeler.",
            "Spatial and temporal transferability requires data from each target management area.",
        ],
        "reproducibility_manifest": {
            "command": "python model_run.py --input <case-json>",
            "python": sys.version,
            "platform": platform.platform(),
            "metrics": metrics,
        },
    }
    output.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()
    summary = load_summary(args.input)
    metrics = build_metrics(summary, args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    figures = write_figures(metrics, Path("figures"))
    metrics["figures"] = figures
    (args.output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    write_report(summary, metrics, args.output_dir / "modeling_report.json")
    manifest = {
        "run_id": "B-mcm-2023-b-002-v2-recovery",
        "command": f"python model_run.py --input {args.input} --output-dir {args.output_dir}",
        "input_path": str(args.input),
        "input_sha256": metrics["input_sha256"],
        "python": sys.version,
        "platform": platform.platform(),
        "random_seed": None,
        "dependencies": {"stdlib_only": True},
        "figures": figures,
        "pending_stages": ["empirical_experiment", "holdout_validation", "sensitivity_robustness", "independent_P1_P2_gate"],
    }
    (args.output_dir / "复现清单.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

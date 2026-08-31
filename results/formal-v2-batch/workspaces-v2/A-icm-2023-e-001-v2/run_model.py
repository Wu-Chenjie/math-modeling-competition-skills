"""Reproducible, data-gated prototype for ICM 2023 Problem E.

The program never synthesizes location observations. It can validate the metric's
mathematical behavior without observations, but location scores and rankings are
only produced when complete rows are supplied in the benchmark summary.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import platform
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, Sequence


SEED = 2023001
INDICATORS = (
    "skyglow",
    "light_trespass",
    "over_illumination",
    "glare",
    "light_clutter",
    "ecological_concern",
    "human_concern",
)
STRATEGIES = {
    # Prototype coefficients are assumptions for mechanics testing, not evidence.
    "shield_and_spectrum": (0.35, 0.50, 0.20, 0.35, 0.15, 0.00, 0.00),
    "adaptive_controls": (0.45, 0.40, 0.40, 0.25, 0.35, 0.00, 0.00),
    "zoning_and_governance": (0.20, 0.25, 0.15, 0.15, 0.40, 0.00, 0.00),
}
STAGES = (
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
)


def clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def composite_risk(
    values: Sequence[float], weights: Sequence[float] | None = None, p: float = 2.0
) -> float:
    """Return a normalized weighted power-mean risk in [0, 1]."""
    if len(values) != len(INDICATORS):
        raise ValueError(f"expected {len(INDICATORS)} indicators")
    if p <= 0:
        raise ValueError("p must be positive")
    if weights is None:
        weights = [1.0 / len(values)] * len(values)
    if len(weights) != len(values) or any(w < 0 for w in weights):
        raise ValueError("weights must be nonnegative and match indicators")
    total = sum(weights)
    if total <= 0:
        raise ValueError("weights must have positive sum")
    normalized_weights = [w / total for w in weights]
    return clamp(sum(w * clamp(x) ** p for x, w in zip(values, normalized_weights)) ** (1.0 / p))


def intervention_effect(values: Sequence[float], strategy: str) -> list[float]:
    """Apply an explicitly assumed fractional reduction vector."""
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy: {strategy}")
    if len(values) != len(INDICATORS):
        raise ValueError(f"expected {len(INDICATORS)} indicators")
    return [clamp(x * (1.0 - reduction)) for x, reduction in zip(values, STRATEGIES[strategy])]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_rows(summary: dict) -> list[dict]:
    rows: list[dict] = []
    for audit in summary.get("data_audit", []):
        candidate = audit.get("rows_data", []) if isinstance(audit, dict) else []
        if isinstance(candidate, list):
            rows.extend(row for row in candidate if isinstance(row, dict))
    return rows


def structural_experiment() -> dict:
    rng = random.Random(SEED)
    violations = {"bounds": 0, "monotonicity": 0, "finite": 0}
    trials = 1000
    for _ in range(trials):
        lower = [rng.random() for _ in INDICATORS]
        upper = [x + (1.0 - x) * rng.random() for x in lower]
        a = composite_risk(lower)
        b = composite_risk(upper)
        violations["bounds"] += int(not (0.0 <= a <= 1.0 and 0.0 <= b <= 1.0))
        violations["monotonicity"] += int(a > b + 1e-12)
        violations["finite"] += int(not (math.isfinite(a) and math.isfinite(b)))

    reference = [i / (len(INDICATORS) - 1) for i in range(len(INDICATORS))]
    p_scores = {str(p): composite_risk(reference, p=p) for p in (1.0, 2.0, 4.0)}
    concentrated_scores = {}
    for index, name in enumerate(INDICATORS):
        weights = [(0.6 / (len(INDICATORS) - 1))] * len(INDICATORS)
        weights[index] = 0.4
        concentrated_scores[name] = composite_risk(reference, weights=weights)

    return {
        "kind": "synthetic_structural_test_not_location_data",
        "seed": SEED,
        "trials": trials,
        "violations": violations,
        "boundary_scores": {
            "all_zero": composite_risk([0.0] * len(INDICATORS)),
            "all_one": composite_risk([1.0] * len(INDICATORS)),
        },
        "p_sensitivity": p_scores,
        "weight_concentration_range": [
            min(concentrated_scores.values()),
            max(concentrated_scores.values()),
        ],
        "weight_concentration_scores": concentrated_scores,
    }


def score_complete_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    scores, rejected = [], []
    for row_index, row in enumerate(rows):
        missing = [name for name in INDICATORS if name not in row or row[name] in (None, "")]
        if missing:
            rejected.append({"row_index": row_index, "missing": missing})
            continue
        try:
            values = [float(row[name]) for name in INDICATORS]
        except (TypeError, ValueError):
            rejected.append({"row_index": row_index, "reason": "non_numeric_indicator"})
            continue
        if any(not 0.0 <= value <= 1.0 for value in values):
            rejected.append({"row_index": row_index, "reason": "indicator_outside_0_1"})
            continue
        scores.append(
            {
                "row_index": row_index,
                "location": row.get("location"),
                "location_type": row.get("location_type"),
                "risk_0_100": 100.0 * composite_risk(values),
            }
        )
    return scores, rejected


def build_report(summary: dict, output_root: Path) -> dict:
    rows = extract_rows(summary)
    scores, rejected = score_complete_rows(rows)
    has_four_types = {
        row.get("location_type") for row in rows if isinstance(row.get("location_type"), str)
    }.issuperset({"protected", "rural", "suburban", "urban"})
    empirical_ready = len(scores) >= 4 and has_four_types
    experiment = structural_experiment()
    pending = []
    if not empirical_ready:
        pending.extend(
            [
                "four_location_empirical_scoring",
                "two_location_strategy_selection",
                "empirical_validation_and_uncertainty",
                "location_specific_flyer",
            ]
        )
    pending.extend(["weight_threshold_calibration", "intervention_effect_calibration", "publication_png_figure_audit"])

    return {
        "problem_framing": {
            "objective": "Measure location-specific light-pollution risk while representing human and non-human concerns, compare three interventions, select strategies for two locations, and support a location-specific flyer.",
            "decision_units": ["protected land", "rural community", "suburban community", "urban community"],
            "required_outputs": ["risk metric", "four applications", "three interventions", "two selections", "one-page flyer"],
        },
        "data_audit": {
            "case_id": summary.get("case_id"),
            "source_status": summary.get("source_status"),
            "problem_sha256_declared": summary.get("problem_sha256"),
            "data_sha256_declared": summary.get("data_sha256"),
            "data_files_count": len(summary.get("data_files", [])),
            "data_audit_entries": len(summary.get("data_audit", [])),
            "rows_available": len(rows),
            "rows_scoreable": len(scores),
            "rows_rejected": rejected,
            "binary_attachments_opened": 0,
            "finding": "No empirical rows are supplied; location scoring is gated off." if not rows else "Supplied rows were schema-validated before scoring.",
        },
        "assumptions": {
            "critical": [
                "Each indicator must be normalized to [0,1] using documented external bounds before scoring.",
                "Indicators and weights must have the same interpretation across location types.",
                "Missing indicators do not receive imputed values in this preregistered run.",
            ],
            "relaxable": [
                "Equal weights are an uncalibrated baseline.",
                "Power exponent p=2 emphasizes high-risk components.",
                "Prototype intervention coefficients test mechanics only and are not effectiveness evidence.",
            ],
        },
        "candidate_models": [
            {
                "name": "weighted_power_mean_MCDA",
                "status": "implemented_baseline",
                "rationale": "Transparent, bounded, monotone, and applicable when indicators use different source units after normalization.",
            },
            {
                "name": "hierarchical_spatial_latent_risk",
                "status": "pending_data",
                "rationale": "Can pool heterogeneous locations and quantify uncertainty when spatial, temporal, and outcome observations exist.",
            },
        ],
        "baseline": {
            "model": "equal-weight quadratic mean",
            "weights": {name: 1.0 / len(INDICATORS) for name in INDICATORS},
            "p": 2.0,
            "location_scores": scores,
            "interpretation": "No empirical risk level is reported without complete supplied observations and calibrated category thresholds.",
        },
        "math_specification": {
            "indicators": list(INDICATORS),
            "normalization": "z_ij=(x_ij-L_j)/(U_j-L_j), clipped to [0,1], with L_j and U_j supplied from documented sources.",
            "risk": "R_i=100*(sum_j w_j*z_ij^p)^(1/p), w_j>=0, sum_j w_j=1, p>0.",
            "intervention": "z'_ij=clip(z_ij*(1-e_jk),0,1); e_jk must be calibrated or explicitly treated as a scenario assumption.",
            "constraints": ["complete indicators", "documented normalization bounds", "nonnegative normalized weights", "no empirical category without calibrated thresholds"],
        },
        "code_prototype": {
            "language": "Python standard library",
            "entrypoint": "python run_model.py --input <case-summary.json> --output .",
            "missing_data_policy": "reject incomplete rows; never impute omitted values",
        },
        "experiment": experiment,
        "validation": {
            "structural_status": "complete" if not any(experiment["violations"].values()) else "failed",
            "empirical_status": "complete" if empirical_ready else "pending",
            "tests": ["range", "boundary", "monotonicity", "finite output", "missing-data gate"],
            "out_of_sample_validation": "pending because no observations or outcomes are supplied",
        },
        "sensitivity_robustness": {
            "status": "structural_only",
            "p_scores_on_deterministic_reference_vector": experiment["p_sensitivity"],
            "weight_concentration_score_range": experiment["weight_concentration_range"],
            "limitation": "These are mathematical stress tests, not location estimates.",
        },
        "falsification": {
            "criteria": [
                "Reject implementation if risk leaves [0,100], is non-finite, or decreases when any adverse indicator increases with others fixed.",
                "Reject transferability if normalization bounds or indicator meanings differ materially by location type.",
                "Reject a strategy ranking if it changes across plausible calibrated weights/effects or violates a safety constraint.",
                "Reject empirical claims without representative samples, outcome validation, and uncertainty intervals.",
            ]
        },
        "reviewer_risks": [
            "No location observations are supplied, so the official four-location application is incomplete.",
            "Equal weights, p=2, normalization bounds, category thresholds, and intervention effects lack calibration.",
            "Potential sampling bias and confounded correlations cannot be assessed without data provenance and outcomes.",
            "The additive separability implicit in the power mean may miss ecological-human interactions.",
            "Safety benefits of artificial light require explicit constraints and stakeholder evidence before intervention choice.",
            "SVG-only figures have not passed the pinned publication PNG/DPI visual audit because matplotlib is unavailable.",
            "Independent M1/P1/P2 Subagent gates were not run because the preregistered instructions did not authorize delegation.",
        ],
        "reproducibility_manifest": {
            "seed": SEED,
            "input_case_id": summary.get("case_id"),
            "input_problem_sha256": summary.get("problem_sha256"),
            "runtime": platform.python_version(),
            "platform": platform.platform(),
            "parameters": {"p": 2.0, "weights": "equal", "indicators": list(INDICATORS)},
        },
        "stage_status": {stage: "complete" for stage in STAGES},
        "pending_stages": pending,
    }


def svg_document(title: str, subtitle: str, body: str, width: int = 760, height: int = 460) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="#ffffff"/>
<text x="55" y="42" font-family="Arial" font-size="21" fill="#222222">{title}</text>
<text x="55" y="68" font-family="Arial" font-size="11" fill="#666666">{subtitle}</text>
<line x1="55" y1="82" x2="720" y2="82" stroke="#cccccc"/>
{body}
</svg>'''


def bar_svg(title: str, subtitle: str, labels: Sequence[str], values: Sequence[float], maximum: float | None = None) -> str:
    maximum = maximum or max(max(values, default=0), 1)
    usable = 600
    rows = []
    for index, (label, value) in enumerate(zip(labels, values)):
        y = 112 + index * 42
        bar_width = usable * value / maximum
        rows.append(f'<text x="55" y="{y + 15}" font-family="Arial" font-size="11" fill="#333333">{label}</text>')
        rows.append(f'<rect x="210" y="{y}" width="{bar_width:.2f}" height="20" fill="#0072B2"/>')
        rows.append(f'<text x="{220 + bar_width:.2f}" y="{y + 15}" font-family="Arial" font-size="11" fill="#333333">{value:g}</text>')
    return svg_document(title, subtitle, "\n".join(rows))


def line_svg(title: str, subtitle: str, series: Sequence[tuple[str, Sequence[tuple[float, float]]]]) -> str:
    colors = ("#0072B2", "#D55E00", "#009E73", "#CC79A7")
    left, top, width, height = 70, 100, 620, 290
    elements = [
        f'<line x1="{left}" y1="{top + height}" x2="{left + width}" y2="{top + height}" stroke="#333333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + height}" stroke="#333333"/>',
        f'<text x="{left + width / 2}" y="430" text-anchor="middle" font-family="Arial" font-size="11">normalized input / reduction</text>',
        f'<text x="18" y="{top + height / 2}" transform="rotate(-90 18 {top + height / 2})" text-anchor="middle" font-family="Arial" font-size="11">normalized risk</text>',
    ]
    for idx, (label, points) in enumerate(series):
        path = " ".join(
            ("M" if i == 0 else "L") + f" {left + x * width:.2f} {top + (1 - y) * height:.2f}"
            for i, (x, y) in enumerate(points)
        )
        color = colors[idx % len(colors)]
        elements.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"/>')
        elements.append(f'<line x1="{505 + idx * 65}" y1="78" x2="{525 + idx * 65}" y2="78" stroke="{color}" stroke-width="2"/>')
        elements.append(f'<text x="{530 + idx * 65}" y="82" font-family="Arial" font-size="10">{label}</text>')
    return svg_document(title, subtitle, "\n".join(elements))


def write_figures(summary: dict, report: dict, output_root: Path) -> list[dict]:
    figures_dir = output_root / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    requirements = [4, 3, 2, 1]
    all_missing = [0] * len(INDICATORS)
    response = []
    for p in (1.0, 2.0, 4.0):
        response.append((f"p={p:g}", [(i / 20, composite_risk([i / 20] + [0.5] * 6, p=p)) for i in range(21)]))
    reduction = [(r / 20, composite_risk([0.5 * (1 - r / 20)] * 7)) for r in range(21)]

    specs = [
        ("raw_q1_input_inventory.svg", bar_svg("Input inventory", "Observed benchmark metadata; no location rows", ["problem text", "data files", "rows"], [1, len(summary.get("data_files", [])), report["data_audit"]["rows_available"]], 1)),
        ("process_q1_metric_response.svg", line_svg("Metric response", "Synthetic structural sweep; not location data", response)),
        ("result_q1_boundary_checks.svg", bar_svg("Metric checks", "Executed structural violations (lower is better)", ["bounds", "monotonicity", "finite"], list(report["experiment"]["violations"].values()), 1)),
        ("raw_q2_location_rows.svg", bar_svg("Location application inputs", "Required types versus supplied scoreable rows", ["required types", "scoreable rows"], [4, report["data_audit"]["rows_scoreable"]], 4)),
        ("process_q2_scoring_gate.svg", bar_svg("Scoring gate", "All seven normalized indicators are required", list(INDICATORS), all_missing, 1)),
        ("result_q2_application_status.svg", bar_svg("Four-location application", "Completed empirical location scores", ["protected", "rural", "suburban", "urban"], [0, 0, 0, 0], 1)),
        ("raw_q3_strategy_requirement.svg", bar_svg("Intervention requirement", "Counts stated in official problem text", ["strategies requested", "strategies specified"], [3, len(STRATEGIES)], 3)),
        ("process_q3_uniform_reduction.svg", line_svg("Intervention transfer", "Uniform synthetic reduction; mechanics only", [("risk", reduction)])),
        ("result_q3_calibration_status.svg", bar_svg("Intervention calibration", "Empirical effect estimates supplied", list(STRATEGIES), [0, 0, 0], 1)),
        ("raw_q4_selection_requirement.svg", bar_svg("Strategy selection requirement", "Counts stated in official problem text", ["locations to select", "eligible supplied locations"], [2, 0], 2)),
        ("process_q4_ranking_inputs.svg", bar_svg("Ranking input readiness", "Calibration sources available", ["location baselines", "effect estimates", "safety constraints"], [0, 0, 0], 1)),
        ("result_q4_selection_status.svg", bar_svg("Strategy selection", "Evidence-backed selections completed", ["required", "completed"], [2, 0], 2)),
        ("raw_q5_flyer_requirement.svg", bar_svg("Flyer requirement", "Counts stated in official problem text", ["location-specific flyers required", "eligible location-strategy pairs"], [1, 0], 1)),
        ("process_q5_evidence_readiness.svg", bar_svg("Flyer evidence readiness", "Required evidence components available", ["location score", "chosen strategy", "estimated impact"], [0, 0, 0], 1)),
        ("result_q5_flyer_status.svg", bar_svg("Flyer status", "Evidence-backed flyers completed", ["required", "completed"], [1, 0], 1)),
    ]
    index = []
    for filename, content in specs:
        path = figures_dir / filename
        path.write_text(content, encoding="utf-8")
        kind, question, _ = filename.split("_", 2)
        index.append(
            {
                "file": str(path.relative_to(output_root)),
                "category": kind,
                "question": question,
                "format": "svg",
                "empirical_location_data": False,
            }
        )
    (figures_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index


def write_csv(report: dict, output_root: Path) -> None:
    results_dir = output_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    with (results_dir / "structural_experiment.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["test", "value", "interpretation"])
        for name, value in report["experiment"]["violations"].items():
            writer.writerow([name + "_violations", value, "synthetic structural test"])
        for name, value in report["experiment"]["boundary_scores"].items():
            writer.writerow([name, value, "analytic boundary"])
        for name, value in report["experiment"]["p_sensitivity"].items():
            writer.writerow(["p=" + name, value, "deterministic reference vector; not location data"])


def markdown_report(report: dict) -> str:
    audit = report["data_audit"]
    exp = report["experiment"]
    pending = "\n".join(f"- {item}" for item in report["pending_stages"])
    risks = "\n".join(f"- {item}" for item in report["reviewer_risks"])
    return f"""# ICM 2023 Problem E: Structured Modeling Report

## Problem Framing

The decision problem is to construct a transferable light-pollution risk metric, apply it to protected, rural, suburban, and urban locations, compare three interventions, select strategies for two locations, and support a one-page location-specific flyer. The metric must account for human and non-human concerns.

## Data Audit

The deterministic case summary is the complete benchmark input. It contains the verified official problem text, {audit['data_files_count']} data files, {audit['data_audit_entries']} audit entries, and {audit['rows_available']} supplied rows. No binary attachment was opened. Therefore no empirical location score, category, or intervention ranking is reported.

## Assumptions

Critical assumptions are complete normalized indicators, stable indicator meaning across location types, and no imputation of missing observations. Relaxable assumptions are equal weights, quadratic aggregation (`p=2`), and explicitly uncalibrated intervention coefficients used only to test mechanics.

## Candidate Models

The implemented baseline is a transparent weighted power-mean multi-criteria model. A hierarchical spatial latent-risk model is the preferred extension once repeated spatial, temporal, exposure, ecological, health, and safety outcomes become available; it is pending because those data are absent.

## Baseline

The baseline assigns equal weight to seven dimensions: {', '.join(INDICATORS)}. It produces no location outputs in this run. Risk-level category thresholds remain pending calibration.

## Math Specification

For normalized adverse indicator `z_ij` and weights `w_j`, `R_i = 100 (sum_j w_j z_ij^p)^(1/p)`, with `w_j >= 0`, `sum w_j = 1`, and `p > 0`. For strategy `k`, `z'_ij = clip(z_ij(1-e_jk),0,1)`. Bounds and effects must come from documented sources before empirical use.

## Code / Prototype

`run_model.py` is a standard-library Python implementation. It validates schema, rejects incomplete rows, computes only supported scores, runs deterministic structural experiments, and writes JSON, CSV, Markdown, SVG, and a reproducibility manifest.

## Experiment

The synthetic structural experiment ran {exp['trials']} dominance trials with seed {exp['seed']}. It observed {exp['violations']['bounds']} bound violations, {exp['violations']['monotonicity']} monotonicity violations, and {exp['violations']['finite']} non-finite results. These are implementation checks, not empirical evidence.

## Validation

Structural validation is `{report['validation']['structural_status']}`. Empirical validation is `{report['validation']['empirical_status']}` because the benchmark contains no observations or outcomes. Out-of-sample error, calibration, uncertainty coverage, and transferability cannot be estimated.

## Sensitivity / Robustness

On a deterministic reference vector, the risk scores for `p=1,2,4` are {json.dumps(exp['p_sensitivity'])}. Concentrating weight 0.4 on each indicator in turn gives a score range of {exp['weight_concentration_range']}. These results diagnose model behavior only.

## Falsification

The implementation fails if outputs leave `[0,100]`, become non-finite, or decrease when an adverse indicator increases. Transferability fails if indicator meanings or normalization bounds differ across locations. A strategy ranking fails if it is unstable under calibrated uncertainty or violates a safety constraint. Empirical claims fail without representative observations and outcome validation.

## Reviewer Risks

{risks}

## Reproducibility Manifest

Seed: `{SEED}`. Unique command and hashes are in `results/reproducibility_manifest.json`. Machine-readable report and metrics are in `results/modeling_report.json` and `results/metrics.json`. Figure provenance is in `figures/index.json`.

## Pending Stages

{pending}
"""


def dependency_versions() -> dict:
    versions = {"python": platform.python_version()}
    for package in ("numpy", "pandas", "matplotlib"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def run_unit_tests(output_root: Path) -> dict:
    command = [sys.executable, "-m", "unittest", "-v"]
    completed = subprocess.run(command, cwd=output_root, text=True, capture_output=True, check=False)
    return {
        "command": "python -m unittest -v",
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path.cwd())
    args = parser.parse_args()
    started = time.perf_counter()
    output_root = args.output.resolve()
    input_path = args.input.resolve()
    summary = json.loads(input_path.read_text(encoding="utf-8"))
    report = build_report(summary, output_root)

    results_dir = output_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures = write_figures(summary, report, output_root)
    write_csv(report, output_root)
    tests = run_unit_tests(output_root)
    report["validation"]["unit_tests"] = tests
    report["reproducibility_manifest"].update(
        {
            "input_path": str(input_path),
            "input_sha256_actual": sha256(input_path),
            "code_sha256": sha256(Path(__file__).resolve()),
            "dependencies": dependency_versions(),
            "unique_command": f'python run_model.py --input "{input_path}" --output .',
        }
    )
    report_path = results_dir / "modeling_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output_root / "modeling_report.md").write_text(markdown_report(report), encoding="utf-8")

    elapsed = time.perf_counter() - started
    metrics = {
        "case_id": summary.get("case_id"),
        "status": "partial_pending_data" if report["pending_stages"] else "complete",
        "input_sha256": sha256(input_path),
        "declared_problem_sha256": summary.get("problem_sha256"),
        "rows_available": report["data_audit"]["rows_available"],
        "location_scores_count": len(report["baseline"]["location_scores"]),
        "structural_trials": report["experiment"]["trials"],
        "structural_violations": report["experiment"]["violations"],
        "figures_count": len(figures),
        "unit_tests_passed": tests["passed"],
        "unit_test_exit_code": tests["exit_code"],
        "runtime_seconds": elapsed,
        "pending_stages": report["pending_stages"],
    }
    (results_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    manifest = report["reproducibility_manifest"] | {
        "metrics_sha256": sha256(results_dir / "metrics.json"),
        "report_sha256": sha256(report_path),
        "figure_count": len(figures),
    }
    (results_dir / "reproducibility_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return 0 if tests["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

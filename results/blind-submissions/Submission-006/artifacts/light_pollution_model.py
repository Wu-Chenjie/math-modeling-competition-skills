"""Data-honest light-pollution metric prototype for ICM 2023 Problem E."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping


HARM_INDICATORS = (
    "skyglow",
    "trespass",
    "glare",
    "clutter",
    "ecological_sensitivity",
    "human_vulnerability",
)
REQUIRED_FIELDS = HARM_INDICATORS + ("lighting_need",)
EXPOSURE_FIELDS = ("skyglow", "trespass", "glare", "clutter")
VULNERABILITY_FIELDS = ("ecological_sensitivity", "human_vulnerability")


class MetricInputError(ValueError):
    """Raised when a location lacks a complete normalized metric record."""


def validate_location_record(record: Mapping[str, float]) -> None:
    missing = [name for name in REQUIRED_FIELDS if name not in record]
    if missing:
        raise MetricInputError(f"missing required normalized fields: {missing}")
    for name in REQUIRED_FIELDS:
        value = record[name]
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise MetricInputError(f"{name} must be a finite number")
        if not 0.0 <= float(value) <= 1.0:
            raise MetricInputError(f"{name} must be normalized to [0, 1]")


def compute_risk(record: Mapping[str, float]) -> dict[str, float]:
    """Compute baseline and interaction-aware risk from normalized observations."""
    validate_location_record(record)
    pressure = sum(float(record[name]) for name in EXPOSURE_FIELDS) / len(EXPOSURE_FIELDS)
    vulnerability = sum(float(record[name]) for name in VULNERABILITY_FIELDS) / len(VULNERABILITY_FIELDS)
    baseline = 100.0 * sum(float(record[name]) for name in HARM_INDICATORS) / len(HARM_INDICATORS)
    risk = 100.0 * pressure * (0.6 + 0.4 * vulnerability)
    return {
        "exposure_pressure": pressure,
        "vulnerability": vulnerability,
        "baseline_score": baseline,
        "risk_score": risk,
        "lighting_need": float(record["lighting_need"]),
    }


def intervention_effect(
    record: Mapping[str, float], reductions: Mapping[str, float]
) -> dict[str, float]:
    """Apply supplied fractional reductions without assuming strategy efficacy."""
    validate_location_record(record)
    unknown = sorted(set(reductions) - set(EXPOSURE_FIELDS))
    if unknown:
        raise MetricInputError(f"reductions may target exposure fields only: {unknown}")
    adjusted = {name: float(record[name]) for name in REQUIRED_FIELDS}
    for name, fraction in reductions.items():
        if not isinstance(fraction, (int, float)) or not 0.0 <= float(fraction) <= 1.0:
            raise MetricInputError(f"reduction for {name} must be in [0, 1]")
        adjusted[name] *= 1.0 - float(fraction)
    return adjusted


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _rows_count(summary: Mapping[str, Any]) -> int:
    rows_data = summary.get("rows_data")
    if rows_data is None:
        return 0
    if isinstance(rows_data, list):
        return len(rows_data)
    if isinstance(rows_data, dict):
        return sum(len(value) for value in rows_data.values() if isinstance(value, list))
    return 0


def audit_input(summary: Mapping[str, Any]) -> dict[str, Any]:
    data_files = summary.get("data_files") or []
    data_audit = summary.get("data_audit") or []
    rows_count = _rows_count(summary)
    return {
        "data_files_count": len(data_files),
        "data_audit_entries_count": len(data_audit),
        "rows_data_count": rows_count,
        "location_records_count": 0,
        "binary_attachments_opened": 0,
        "can_score_locations": bool(rows_count),
    }


def structural_experiment() -> dict[str, Any]:
    points = [index / 100.0 for index in range(101)]
    values = [[100.0 * pressure * (0.6 + 0.4 * vulnerability)
               for vulnerability in points] for pressure in points]
    violations_pressure = sum(
        values[i + 1][j] + 1e-12 < values[i][j]
        for i in range(100) for j in range(101)
    )
    violations_vulnerability = sum(
        values[i][j + 1] + 1e-12 < values[i][j]
        for i in range(101) for j in range(100)
    )
    return {
        "grid_points": 10201,
        "score_min": min(map(min, values)),
        "score_max": max(map(max, values)),
        "monotonicity_violations_pressure": violations_pressure,
        "monotonicity_violations_vulnerability": violations_vulnerability,
        "pressure_slope_range": [60.0, 100.0],
        "vulnerability_slope_range": [0.0, 40.0],
        "interpretation": "Analytical response audit only; not a location experiment.",
    }


def make_figures(summary: Mapping[str, Any], audit: Mapping[str, Any], root: Path) -> list[str]:
    figure_dir = root / "figures"
    figure_dir.mkdir(exist_ok=True)
    paths: list[str] = []

    def write_svg(filename: str, title: str, lines: list[str]) -> None:
        escaped = [line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for line in lines]
        text_nodes = "".join(
            f'<text x="60" y="{110 + 34*i}" font-family="Arial" font-size="18">{line}</text>'
            for i, line in enumerate(escaped)
        )
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">'
               f'<rect width="900" height="420" fill="#f7f9fb"/><text x="60" y="60" '
               f'font-family="Arial" font-size="26" font-weight="bold">{title}</text>{text_nodes}</svg>')
        path = figure_dir / filename
        path.write_text(svg, encoding="utf-8")
        paths.append(str(path.relative_to(root)))

    write_svg("raw_q1_input_availability.svg", "Input availability audit", [
        f"Data files: {audit['data_files_count']}",
        f"Audit entries: {audit['data_audit_entries_count']}",
        f"Supplied rows: {audit['rows_data_count']}",
        "No empirical location values were supplied or inferred.",
    ])
    write_svg("process_q1_structural_response.svg", "Structural response audit", [
        "R = 100 P (0.6 + 0.4 V)",
        "Domain: P,V in [0,1]; score range: 0-100",
        "Monotonicity checked analytically on a 101 x 101 grid.",
    ])
    write_svg("result_q1_metric_contract.svg", "Metric contract", [
        "P = mean(skyglow, trespass, glare, clutter)",
        "V = mean(ecological sensitivity, human vulnerability)",
        "Location scoring pending complete normalized records.",
    ])
    for q, title in [(2, "Four-location application"), (3, "Intervention strategies"),
                     (4, "Strategy selection"), (5, "Promotion flyer")]:
        for kind in ("raw", "process", "result"):
            write_svg(f"{kind}_q{q}_pending.svg", title, [
                "Pending: deterministic summary contains no location rows.",
                "No values, rankings, or intervention effects are fabricated.",
            ])
    return paths


def build_report(summary: Mapping[str, Any], audit: Mapping[str, Any], metrics: Mapping[str, Any]) -> str:
    pending = metrics["pending_stages"]
    return f"""# Light Pollution Modeling Report

## Problem framing
The task requires a broadly applicable light-pollution risk metric, application to protected, rural, suburban, and urban locations, three interventions, intervention selection for two locations, and a one-page flyer. The supplied deterministic summary contains the official problem text but no location observations. This report therefore specifies and structurally tests a metric while withholding all empirical scores and rankings.

## Data audit
- Case: `{summary.get('case_id')}`; source status: `{summary.get('source_status')}`.
- Data files: {audit['data_files_count']}; audit entries: {audit['data_audit_entries_count']}; supplied rows: {audit['rows_data_count']}.
- Binary attachments opened: 0. No location record can be scored.

## Assumptions
Each indicator must be normalized to [0,1] using documented, location-appropriate reference thresholds before scoring. Higher exposure and vulnerability mean higher risk. `lighting_need` is retained as an intervention feasibility constraint, not used to lower pollution harm. The 0.6/0.4 exposure-vulnerability blend is a transparent prototype parameter, not an empirically calibrated coefficient.

## Candidate models
1. Equal-weight additive baseline: simple and auditable, but fully compensatory.
2. Interaction-aware exposure-vulnerability metric (recommended prototype): prevents vulnerability from creating risk without exposure while increasing harm where vulnerable receptors coincide with exposure.
3. Multi-criteria outranking: suitable when stakeholder vetoes and non-compensatory thresholds are elicited, but impossible to calibrate from the supplied input.

## Baseline
For six normalized harm indicators, `B = 100 * mean(x_i)`. It is implemented only for complete user-supplied records; no benchmark location receives a baseline score.

## Math specification
Let `P` be the mean of skyglow, trespass, glare, and clutter; let `V` be the mean of ecological sensitivity and human vulnerability. The prototype is `R = 100 P (0.6 + 0.4 V)`. Thus `0 <= R <= 100`, `dR/dP = 100(0.6+0.4V) >= 0`, and `dR/dV = 40P >= 0`. Risk-band cutoffs remain pending calibration. Interventions accept externally justified reductions `delta_j` and update exposure as `x'_j=x_j(1-delta_j)`; the code supplies no strategy efficacy values.

## Code/prototype
`light_pollution_model.py` validates complete normalized records, computes the baseline and recommended metric, applies supplied intervention reductions, audits the deterministic summary, runs unit tests, creates metrics, and writes figures and a reproducibility manifest.

## Experiment
A 101-by-101 analytical grid checks the formula over all combinations of aggregate exposure and vulnerability in [0,1]. This is a model-response audit, not synthetic or observed location evidence. Grid points: {metrics['experiment']['grid_points']}; score range: {metrics['experiment']['score_min']:.1f}-{metrics['experiment']['score_max']:.1f}.

## Validation
The executable test suite checks bounds/monotonic direction, refusal of incomplete records, and non-increase of exposure under explicitly supplied reductions. Pressure monotonicity violations: {metrics['experiment']['monotonicity_violations_pressure']}; vulnerability monotonicity violations: {metrics['experiment']['monotonicity_violations_vulnerability']}.

## Sensitivity/robustness
Across the normalized domain, sensitivity to exposure lies in [60,100] score units per unit `P`, while sensitivity to vulnerability lies in [0,40] per unit `V`. Weight uncertainty, normalization thresholds, measurement error, and intervention-effect uncertainty cannot be evaluated without data and stakeholder inputs.

## Falsification
Reject or revise the prototype if calibrated indicators violate expected monotonicity, if measured post-intervention exposure increases under an intervention claimed to reduce it, if rankings are unstable under defensible normalization/weight ranges, or if out-of-sample harm outcomes are not ordered by predicted risk. None can be tested on the supplied zero-row input.

## Reviewer risks
The blend coefficient and equal within-group weights are uncalibrated; indicator definitions need operational units and sources; location sampling could be biased; correlations could be confounded; intervention benefits and safety trade-offs are not quantified; risk bands and strategy rankings would be unsupported. No literature citations are asserted because none were supplied or searched in this preregistered input.

## Reproducibility manifest
Input SHA-256: `{metrics['provenance']['case_summary_sha256']}`. Random seed: none (deterministic). Runtime: Python {metrics['reproducibility']['python_version']}. Command: `{metrics['reproducibility']['command']}`. Pending stages: {', '.join(pending)}.
"""


def run_tests(root: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_light_pollution_model.py"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    output = (completed.stdout + completed.stderr).strip()
    if completed.returncode != 0:
        raise RuntimeError(f"unit tests failed:\n{output}")
    return {"command": "python -m unittest -v test_light_pollution_model.py",
            "exit_code": completed.returncode, "tests_run": 3, "status": "passed"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-summary", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    summary_path = args.case_summary.resolve()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("case_id") != "icm-2023-e":
        raise ValueError("unexpected case summary")

    tests = run_tests(root)
    audit = audit_input(summary)
    experiment = structural_experiment()
    figure_paths = make_figures(summary, audit, root)
    pending = [
        "location_indicator_calibration",
        "four_location_scoring_and_interpretation",
        "empirical_intervention_effect_estimation",
        "two_location_strategy_optimization",
        "one_page_location_flyer",
        "uncertainty_and_out_of_sample_validation",
        "independent_domain_stage_gates",
    ]
    command = f'python light_pollution_model.py --case-summary "{summary_path}"'
    metrics = {
        "status": "partial_data_limited",
        "provenance": {
            "case_id": summary["case_id"],
            "source_status": summary.get("source_status"),
            "problem_sha256_from_summary": summary.get("problem_sha256"),
            "case_summary_sha256": sha256_file(summary_path),
        },
        "data_audit": audit,
        "model": {
            "name": "interaction_aware_exposure_vulnerability_metric",
            "formula": "R = 100 * P * (0.6 + 0.4 * V)",
            "exposure_fields": list(EXPOSURE_FIELDS),
            "vulnerability_fields": list(VULNERABILITY_FIELDS),
            "service_constraint_field": "lighting_need",
            "risk_bands": None,
            "calibration_status": "pending",
        },
        "baseline": {"formula": "B = 100 * arithmetic_mean(six harm indicators)",
                     "scores_computed": 0},
        "experiment": experiment,
        "validation": tests,
        "sensitivity": {
            "analytical_only": True,
            "pressure_slope_range": experiment["pressure_slope_range"],
            "vulnerability_slope_range": experiment["vulnerability_slope_range"],
            "empirical_robustness": "pending",
        },
        "falsification": {
            "empirical_tests_completed": 0,
            "criteria_defined": 4,
            "status": "pending_data",
        },
        "figures": figure_paths,
        "pending_stages": pending,
        "reproducibility": {
            "command": command,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "random_seed": None,
            "binary_attachments_opened": 0,
        },
    }

    results_dir = root / "results"
    results_dir.mkdir(exist_ok=True)
    metrics_path = results_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=True, indent=2), encoding="utf-8")
    manifest_path = results_dir / "reproducibility_manifest.json"
    manifest_path.write_text(json.dumps(metrics["reproducibility"], ensure_ascii=True, indent=2),
                             encoding="utf-8")
    report_path = root / "modeling_report.md"
    report_path.write_text(build_report(summary, audit, metrics), encoding="utf-8")

    receipt = {
        "status": "partial_data_limited",
        "code_path": str(Path(__file__).resolve()),
        "metrics_path": str(metrics_path.resolve()),
        "figures_count": len(figure_paths),
        "tests": tests,
        "pending_stages": pending,
    }
    print(json.dumps(receipt, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

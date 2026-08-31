#!/usr/bin/env python3
"""Deterministic, data-free prototype for ICM 2023 Problem E.

This program never treats generated parameter points as observations. It verifies
the proposed metric on a normalized design lattice and writes auditable outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import platform
import sys
from pathlib import Path
from statistics import fmean


PRESSURE_WEIGHTS = (0.30, 0.25, 0.25, 0.20)
VULNERABILITY_WEIGHTS = (0.60, 0.40)
LEVELS = (0.0, 0.25, 0.5, 0.75, 1.0)
STRATEGIES = ("shielding", "spectral_control", "adaptive_dimming")


def validate_unit(values: tuple[float, ...]) -> None:
    if any(not 0.0 <= value <= 1.0 for value in values):
        raise ValueError("All metric inputs must be normalized to [0, 1].")


def pressure_index(pressures: tuple[float, float, float, float]) -> float:
    """Noisy-OR aggregation: multiple pressures compound without double counting."""
    validate_unit(pressures)
    survival = math.prod((1.0 - x) ** w for x, w in zip(pressures, PRESSURE_WEIGHTS))
    return 1.0 - survival


def vulnerability_index(vulnerabilities: tuple[float, float]) -> float:
    validate_unit(vulnerabilities)
    return sum(w * x for x, w in zip(vulnerabilities, VULNERABILITY_WEIGHTS))


def interaction_risk(
    pressures: tuple[float, float, float, float],
    vulnerabilities: tuple[float, float],
) -> float:
    """Dimensionless 0-100 hazard-times-vulnerability risk score."""
    return 100.0 * pressure_index(pressures) * vulnerability_index(vulnerabilities)


def additive_baseline(
    pressures: tuple[float, float, float, float],
    vulnerabilities: tuple[float, float],
) -> float:
    """Transparent comparator that does not encode exposure-vulnerability interaction."""
    validate_unit(pressures + vulnerabilities)
    return 50.0 * (fmean(pressures) + fmean(vulnerabilities))


def apply_strategy(
    name: str,
    pressures: tuple[float, float, float, float],
    vulnerabilities: tuple[float, float],
    efficacy: float,
) -> tuple[tuple[float, float, float, float], tuple[float, float]]:
    """Hypothesis mappings used only for parameter-regime experiments."""
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}")
    if not 0.0 <= efficacy <= 1.0:
        raise ValueError("Efficacy must be in [0, 1].")
    p = list(pressures)
    v = list(vulnerabilities)
    if name == "shielding":
        p[1] *= 1.0 - efficacy
        p[3] *= 1.0 - efficacy
    elif name == "spectral_control":
        v[0] *= 1.0 - efficacy
        v[1] *= 1.0 - 0.75 * efficacy
    else:
        p = [x * (1.0 - efficacy) for x in p]
    return tuple(p), tuple(v)  # type: ignore[return-value]


def intervention_objective(
    name: str,
    pressures: tuple[float, float, float, float],
    vulnerabilities: tuple[float, float],
    efficacy: float,
    safety_dependence: float,
    safety_penalty_weight: float,
) -> float:
    new_p, new_v = apply_strategy(name, pressures, vulnerabilities, efficacy)
    penalty = 0.0
    if name == "adaptive_dimming":
        penalty = 100.0 * safety_penalty_weight * safety_dependence * efficacy**2
    return interaction_risk(new_p, new_v) + penalty


def quantile(sorted_values: list[float], probability: float) -> float:
    position = probability * (len(sorted_values) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return sorted_values[lower]
    fraction = position - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def summarize(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {
        "min": ordered[0],
        "q05": quantile(ordered, 0.05),
        "median": quantile(ordered, 0.50),
        "mean": fmean(ordered),
        "q95": quantile(ordered, 0.95),
        "max": ordered[-1],
    }


def sensitivity_at_midpoint(delta: float = 0.01) -> dict[str, float]:
    center = [0.5] * 6
    labels = ("skyglow", "trespass", "glare", "clutter", "ecology", "circadian")
    derivatives: dict[str, float] = {}
    for index, label in enumerate(labels):
        low = center.copy()
        high = center.copy()
        low[index] -= delta
        high[index] += delta
        low_risk = interaction_risk(tuple(low[:4]), tuple(low[4:]))
        high_risk = interaction_risk(tuple(high[:4]), tuple(high[4:]))
        derivatives[label] = (high_risk - low_risk) / (2.0 * delta)
    return derivatives


def run_tests() -> dict[str, object]:
    checks: list[tuple[str, bool]] = []
    checks.append(("interaction_zero_boundary", interaction_risk((0, 0, 0, 0), (1, 1)) == 0.0))
    checks.append(("interaction_upper_boundary", abs(interaction_risk((1, 1, 1, 1), (1, 1)) - 100.0) < 1e-12))
    checks.append(("baseline_upper_boundary", additive_baseline((1, 1, 1, 1), (1, 1)) == 100.0))
    checks.append(("baseline_confounds_unexposed_vulnerability", additive_baseline((0, 0, 0, 0), (1, 1)) > 0.0))

    monotonic_cases = 0
    monotonic_failures = 0
    for point in itertools.product(LEVELS, repeat=6):
        base = interaction_risk(tuple(point[:4]), tuple(point[4:]))
        for index, value in enumerate(point):
            if value == 1.0:
                continue
            increased = list(point)
            increased[index] = min(1.0, value + 0.25)
            candidate = interaction_risk(tuple(increased[:4]), tuple(increased[4:]))
            monotonic_cases += 1
            if candidate + 1e-12 < base:
                monotonic_failures += 1
    checks.append(("componentwise_monotonicity", monotonic_failures == 0))

    efficacy_cases = 0
    efficacy_failures = 0
    base_p = (0.5, 0.5, 0.5, 0.5)
    base_v = (0.5, 0.5)
    for strategy in STRATEGIES:
        previous = interaction_risk(base_p, base_v)
        for efficacy in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6):
            p2, v2 = apply_strategy(strategy, base_p, base_v, efficacy)
            current = interaction_risk(p2, v2)
            efficacy_cases += 1
            if current > previous + 1e-12:
                efficacy_failures += 1
            previous = current
    checks.append(("unpenalized_efficacy_monotonicity", efficacy_failures == 0))
    failed = [name for name, passed in checks if not passed]
    return {
        "checks": [{"name": name, "passed": passed} for name, passed in checks],
        "assertions": len(checks),
        "failed": failed,
        "monotonic_cases": monotonic_cases,
        "monotonic_failures": monotonic_failures,
        "efficacy_cases": efficacy_cases,
        "efficacy_failures": efficacy_failures,
    }


def strategy_regimes() -> dict[str, object]:
    wins = {name: 0 for name in STRATEGIES}
    ties = 0
    cases = 0
    for pressures in itertools.product((0.25, 0.5, 0.75), repeat=4):
        for vulnerabilities in itertools.product((0.25, 0.5, 0.75), repeat=2):
            for efficacy in (0.2, 0.4, 0.6):
                for safety in (0.0, 0.5, 1.0):
                    for penalty_weight in (0.0, 0.25, 0.5):
                        objectives = {
                            name: intervention_objective(
                                name,
                                pressures,
                                vulnerabilities,
                                efficacy,
                                safety,
                                penalty_weight,
                            )
                            for name in STRATEGIES
                        }
                        best = min(objectives.values())
                        winners = [name for name, value in objectives.items() if abs(value - best) < 1e-10]
                        cases += 1
                        if len(winners) == 1:
                            wins[winners[0]] += 1
                        else:
                            ties += 1
    return {"parameter_cases": cases, "unique_wins": wins, "ties": ties}


def svg_line_chart(path: Path, title: str, series: dict[str, list[tuple[float, float]]], x_label: str, y_label: str) -> None:
    width, height = 760, 460
    left, right, top, bottom = 80, 30, 55, 70
    plot_w, plot_h = width - left - right, height - top - bottom
    xs = [x for points in series.values() for x, _ in points]
    ys = [y for points in series.values() for _, y in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if math.isclose(ymin, ymax):
        ymax = ymin + 1.0
    colors = ("#0072B2", "#D55E00", "#009E73", "#CC79A7")

    def sx(x: float) -> float:
        return left + (x - xmin) / (xmax - xmin or 1.0) * plot_w

    def sy(y: float) -> float:
        return top + plot_h - (y - ymin) / (ymax - ymin) * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="30" text-anchor="middle" font-family="Arial" font-size="18">{title}</text>',
        f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#333"/>',
        f'<text x="{left+plot_w/2}" y="{height-20}" text-anchor="middle" font-family="Arial" font-size="14">{x_label}</text>',
        f'<text x="18" y="{top+plot_h/2}" text-anchor="middle" transform="rotate(-90 18 {top+plot_h/2})" font-family="Arial" font-size="14">{y_label}</text>',
    ]
    for tick in range(6):
        x_value = xmin + tick * (xmax - xmin) / 5
        y_value = ymin + tick * (ymax - ymin) / 5
        x_pos, y_pos = sx(x_value), sy(y_value)
        parts.extend([
            f'<line x1="{x_pos:.2f}" y1="{top}" x2="{x_pos:.2f}" y2="{top+plot_h}" stroke="#ddd"/>',
            f'<text x="{x_pos:.2f}" y="{top+plot_h+22}" text-anchor="middle" font-family="Arial" font-size="11">{x_value:.2f}</text>',
            f'<line x1="{left}" y1="{y_pos:.2f}" x2="{left+plot_w}" y2="{y_pos:.2f}" stroke="#ddd"/>',
            f'<text x="{left-10}" y="{y_pos+4:.2f}" text-anchor="end" font-family="Arial" font-size="11">{y_value:.1f}</text>',
        ])
    for index, (name, points) in enumerate(series.items()):
        color = colors[index % len(colors)]
        coords = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in points)
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="3"/>')
        legend_y = 65 + index * 20
        parts.append(f'<line x1="{width-190}" y1="{legend_y}" x2="{width-165}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>')
        parts.append(f'<text x="{width-158}" y="{legend_y+4}" font-family="Arial" font-size="12">{name}</text>')
    parts.append('</svg>')
    path.write_text("\n".join(parts), encoding="utf-8")


def generate_figures(figures_dir: Path, sensitivity: dict[str, float]) -> list[str]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []

    exposure = [i / 20 for i in range(21)]
    for filename, title, vulnerabilities in (
        ("raw_q1_metric_domain.svg", "Metric domain at fixed vulnerability", (0.25, 0.5, 0.75)),
        ("raw_q3_efficacy_domain.svg", "Strategy efficacy domain", (0.2, 0.4, 0.6)),
        ("raw_q4_safety_domain.svg", "Adaptive dimming safety trade-off", (0.0, 0.5, 1.0)),
    ):
        if "metric" in filename:
            series = {f"V={v:.2f}": [(x, interaction_risk((x, x, x, x), (v, v))) for x in exposure] for v in vulnerabilities}
            x_label = "Common normalized pressure"
        elif "efficacy" in filename:
            series = {
                name: [(e, intervention_objective(name, (0.5,)*4, (0.5,)*2, e, 0.5, 0.25)) for e in exposure]
                for name in STRATEGIES
            }
            x_label = "Hypothetical efficacy"
        else:
            series = {
                f"Safety={s:.1f}": [(e, intervention_objective("adaptive_dimming", (0.5,)*4, (0.5,)*2, e, s, 0.5)) for e in exposure]
                for s in vulnerabilities
            }
            x_label = "Hypothetical efficacy"
        svg_line_chart(figures_dir / filename, title, series, x_label, "Dimensionless objective")
        generated.append(filename)

    for filename, title, varying in (
        ("process_q1_model_response.svg", "Interaction and additive response", "model"),
        ("process_q3_strategy_response.svg", "Strategy response at equal efficacy", "strategy"),
        ("process_q4_penalty_response.svg", "Penalty-weight robustness", "penalty"),
    ):
        if varying == "model":
            series = {
                "interaction": [(x, interaction_risk((x,)*4, (0.5,)*2)) for x in exposure],
                "additive": [(x, additive_baseline((x,)*4, (0.5,)*2)) for x in exposure],
            }
            x_label = "Common normalized pressure"
        elif varying == "strategy":
            series = {name: [(e, intervention_objective(name, (0.5,)*4, (0.5,)*2, e, 0.5, 0.25)) for e in exposure] for name in STRATEGIES}
            x_label = "Hypothetical efficacy"
        else:
            series = {
                f"lambda={weight:.2f}": [(e, intervention_objective("adaptive_dimming", (0.5,)*4, (0.5,)*2, e, 0.75, weight)) for e in exposure]
                for weight in (0.0, 0.25, 0.5)
            }
            x_label = "Hypothetical efficacy"
        svg_line_chart(figures_dir / filename, title, series, x_label, "Dimensionless score")
        generated.append(filename)

    sensitivity_points = list(enumerate(sensitivity.values()))
    svg_line_chart(
        figures_dir / "result_q1_local_sensitivity.svg",
        "Local sensitivity at normalized midpoint",
        {"partial derivative": sensitivity_points},
        "Indicator index",
        "Risk points per unit",
    )
    generated.append("result_q1_local_sensitivity.svg")
    svg_line_chart(
        figures_dir / "result_q3_strategy_comparison.svg",
        "Parameterized strategy comparison",
        {name: [(e, intervention_objective(name, (0.6,)*4, (0.6,)*2, e, 0.5, 0.25)) for e in exposure] for name in STRATEGIES},
        "Hypothetical efficacy",
        "Dimensionless objective",
    )
    generated.append("result_q3_strategy_comparison.svg")
    svg_line_chart(
        figures_dir / "result_q4_safety_robustness.svg",
        "Safety dependence robustness",
        {f"Safety={s:.1f}": [(e, intervention_objective("adaptive_dimming", (0.6,)*4, (0.6,)*2, e, s, 0.4)) for e in exposure] for s in (0.0, 0.5, 1.0)},
        "Hypothetical efficacy",
        "Dimensionless objective",
    )
    generated.append("result_q4_safety_robustness.svg")
    return generated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-summary", required=True, type=Path)
    parser.add_argument("--output-root", default=Path(__file__).resolve().parent, type=Path)
    args = parser.parse_args()

    source_bytes = args.case_summary.read_bytes()
    case = json.loads(source_bytes.decode("utf-8"))
    if case.get("case_id") != "icm-2023-e":
        raise ValueError("Unexpected benchmark case_id")
    if case.get("data_files") or case.get("data_audit") or case.get("zip_entries"):
        raise ValueError("This preregistered prototype expects the audited no-data case summary.")

    root = args.output_root.resolve()
    results_dir = root / "results"
    figures_dir = root / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)

    interaction_values: list[float] = []
    baseline_values: list[float] = []
    for point in itertools.product(LEVELS, repeat=6):
        pressures = tuple(point[:4])
        vulnerabilities = tuple(point[4:])
        interaction_values.append(interaction_risk(pressures, vulnerabilities))
        baseline_values.append(additive_baseline(pressures, vulnerabilities))

    sensitivity = sensitivity_at_midpoint()
    tests = run_tests()
    regimes = strategy_regimes()
    figure_names = generate_figures(figures_dir, sensitivity)

    metrics = {
        "case_id": case["case_id"],
        "input_mode": "synthetic_parameter_lattice_no_observational_data",
        "observational_claims_permitted": False,
        "case_summary_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "official_problem_sha256": case.get("problem_sha256"),
        "data_audit": {
            "data_files_count": len(case.get("data_files", [])),
            "audited_entries_count": len(case.get("data_audit", [])),
            "rows_available": 0,
        },
        "experiment": {
            "levels": list(LEVELS),
            "dimensions": 6,
            "lattice_cases": len(interaction_values),
            "interaction_metric": summarize(interaction_values),
            "additive_baseline": summarize(baseline_values),
            "midpoint_sensitivity": sensitivity,
            "strategy_regimes": regimes,
        },
        "validation": tests,
        "figures": figure_names,
        "pending_stages": [
            "empirical_four_location_application: no location observations or rows in benchmark input",
            "calibrated_two_location_intervention_selection: no location observations or intervention effect estimates",
            "location_specific_flyer: no empirically supported location-strategy selection",
            "external_validation: benchmark input supplies no validation observations",
        ],
    }
    metrics_path = results_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with (results_dir / "grid_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("model", "min", "q05", "median", "mean", "q95", "max"))
        for name, values in (("interaction", interaction_values), ("additive_baseline", baseline_values)):
            summary = summarize(values)
            writer.writerow((name,) + tuple(summary[key] for key in ("min", "q05", "median", "mean", "q95", "max")))

    manifest = {
        "case_summary": str(args.case_summary.resolve()),
        "case_summary_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "code_path": str(Path(__file__).resolve()),
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python": platform.python_version(),
        "random_seed": None,
        "randomness_used": False,
        "unique_command": f'python "{Path(__file__).resolve()}" --case-summary "{args.case_summary.resolve()}" --output-root "{root}"',
    }
    (results_dir / "repro_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    passed = not tests["failed"] and len(figure_names) == 9
    receipt = {
        "status": "completed_with_pending_stages" if passed else "failed_validation",
        "code_path": str(Path(__file__).resolve()),
        "metrics_path": str(metrics_path.resolve()),
        "figures_count": len(figure_names),
        "tests": {
            "status": "passed" if passed else "failed",
            "assertions": tests["assertions"],
            "failed": tests["failed"],
            "monotonic_cases": tests["monotonic_cases"],
            "monotonic_failures": tests["monotonic_failures"],
        },
        "pending_stages": metrics["pending_stages"],
    }
    print(json.dumps(receipt, separators=(",", ":")))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

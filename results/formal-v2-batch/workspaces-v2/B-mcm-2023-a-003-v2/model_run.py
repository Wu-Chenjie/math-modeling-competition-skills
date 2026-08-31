#!/usr/bin/env python3
"""Reproducible scenario model for MCM 2023 Problem A.

The benchmark supplies no empirical data rows. Parameters below are dimensionless,
hypothetical scenario assumptions and must not be interpreted as fitted estimates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean
from time import perf_counter


INPUT_SHA256 = "948959869a6e863246b0eb7c9001e82a39b9b28d8ffe881fcd8aad5bddfc9002"
SEED = 2023003


@dataclass(frozen=True)
class Scenario:
    name: str
    drought_frequency: float
    drought_variability: float
    pollution: float = 0.0
    habitat_loss: float = 0.0


SCENARIOS = (
    Scenario("low_drought", 0.10, 0.15),
    Scenario("reference", 0.25, 0.25),
    Scenario("future_drought", 0.45, 0.35),
    Scenario("future_plus_stress", 0.45, 0.35, pollution=0.10, habitat_loss=0.20),
)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def generate_weather(years: int, scenario: Scenario, seed: int) -> list[float]:
    """Return annual drought severity in [0, 1], including clustered droughts."""
    rng = random.Random(seed)
    severities: list[float] = []
    previous_drought = False
    for _ in range(years):
        probability = clamp(
            scenario.drought_frequency + (0.16 if previous_drought else 0.0), 0.0, 0.95
        )
        drought = rng.random() < probability
        if drought:
            severity = clamp(rng.gauss(0.55, scenario.drought_variability), 0.12, 1.0)
        else:
            severity = clamp(rng.gauss(0.04, 0.03), 0.0, 0.12)
        severities.append(severity)
        previous_drought = drought
    return severities


def species_traits(richness: int) -> list[float]:
    """Evenly span a drought-sensitivity trait axis; lower is more tolerant."""
    if richness == 1:
        return [0.65]
    return [0.25 + 0.75 * i / (richness - 1) for i in range(richness)]


def simulate(
    richness: int,
    scenario: Scenario,
    years: int = 120,
    seed: int = SEED,
    identical_traits: bool = False,
) -> dict:
    """Simulate biomass using a nonnegative discrete generalized LV model."""
    traits = [0.65] * richness if identical_traits else species_traits(richness)
    weather = generate_weather(years, scenario, seed)
    carrying_capacity = 100.0 * (1.0 - scenario.habitat_loss)
    biomass = [carrying_capacity * 0.45 / richness] * richness
    adaptation = [0.0] * richness
    totals: list[float] = []
    diversities: list[float] = []
    dt = 0.20

    for severity in weather:
        for _ in range(5):
            total = sum(biomass)
            updated = []
            for i, current in enumerate(biomass):
                competition = current + 0.72 * (total - current)
                drought_damage = severity * traits[i] * (1.0 - 0.55 * adaptation[i])
                growth = 0.72 * (1.0 - drought_damage)
                mortality = 0.16 + scenario.pollution + 0.14 * drought_damage
                derivative = current * (
                    growth * (1.0 - competition / max(carrying_capacity, 1e-12)) - mortality
                )
                updated.append(max(0.0, current + dt * derivative))
            biomass = updated
        for i in range(richness):
            # Local adaptive memory carries a tolerance benefit but has a maintenance cost.
            adaptation[i] = clamp(
                adaptation[i]
                + 0.09 * severity * (1.0 - adaptation[i])
                - 0.018 * adaptation[i],
                0.0,
                1.0,
            )
        total = sum(biomass)
        totals.append(total)
        if total > 0:
            proportions = [value / total for value in biomass if value > 0]
            diversities.append(math.exp(-sum(p * math.log(p) for p in proportions)))
        else:
            diversities.append(0.0)

    tail = totals[-30:]
    mean_tail = fmean(tail)
    variability = (math.sqrt(fmean([(x - mean_tail) ** 2 for x in tail])) / mean_tail) if mean_tail else None
    return {
        "richness": richness,
        "scenario": scenario.name,
        "years": years,
        "weather": weather,
        "total_biomass": totals,
        "effective_diversity": diversities,
        "final_species_biomass": biomass,
        "mean_last_30": mean_tail,
        "min_last_30": min(tail),
        "cv_last_30": variability,
        "persistence_fraction": sum(value > 1.0 for value in biomass) / richness,
    }


def summarize_runs(runs: list[dict]) -> list[dict]:
    return [
        {
            "scenario": run["scenario"],
            "richness": run["richness"],
            "mean_last_30": round(run["mean_last_30"], 6),
            "min_last_30": round(run["min_last_30"], 6),
            "cv_last_30": None if run["cv_last_30"] is None else round(run["cv_last_30"], 6),
            "persistence_fraction": round(run["persistence_fraction"], 6),
        }
        for run in runs
    ]


def minimum_beneficial_richness(rows: list[dict], scenario: str, threshold: float = 0.05) -> int | None:
    selected = sorted((row for row in rows if row["scenario"] == scenario), key=lambda row: row["richness"])
    baseline = selected[0]["mean_last_30"]
    for row in selected[1:]:
        if row["mean_last_30"] >= baseline * (1.0 + threshold):
            return row["richness"]
    return None


def svg_line_chart(path: Path, title: str, x_label: str, y_label: str, series: dict[str, tuple[list[float], list[float]]]) -> None:
    width, height = 900, 560
    left, right, top, bottom = 90, 30, 65, 75
    all_x = [x for xs, _ in series.values() for x in xs]
    all_y = [y for _, ys in series.values() for y in ys]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    if y_max == y_min:
        y_max += 1.0
    colors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"]

    def sx(value: float) -> float:
        return left + (value - x_min) / max(x_max - x_min, 1e-12) * (width - left - right)

    def sy(value: float) -> float:
        return top + (y_max - value) / (y_max - y_min) * (height - top - bottom)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="32" text-anchor="middle" font-family="Arial" font-size="21">{title}</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#222"/>',
    ]
    for tick in range(6):
        value = y_min + (y_max - y_min) * tick / 5
        y = sy(value)
        parts.extend([
            f'<line x1="{left}" y1="{y:.2f}" x2="{width-right}" y2="{y:.2f}" stroke="#ddd"/>',
            f'<text x="{left-9}" y="{y+5:.2f}" text-anchor="end" font-family="Arial" font-size="13">{value:.1f}</text>',
        ])
    for idx, (name, (xs, ys)) in enumerate(series.items()):
        color = colors[idx % len(colors)]
        points = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in zip(xs, ys))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for x, y in zip(xs, ys):
            parts.append(f'<circle cx="{sx(x):.2f}" cy="{sy(y):.2f}" r="3" fill="{color}"/>')
        ly = 53 + idx * 22
        parts.extend([
            f'<line x1="{width-230}" y1="{ly}" x2="{width-200}" y2="{ly}" stroke="{color}" stroke-width="3"/>',
            f'<text x="{width-190}" y="{ly+5}" font-family="Arial" font-size="13">{name}</text>',
        ])
    parts.extend([
        f'<text x="{width/2}" y="{height-22}" text-anchor="middle" font-family="Arial" font-size="15">{x_label}</text>',
        f'<text x="22" y="{height/2}" transform="rotate(-90 22 {height/2})" text-anchor="middle" font-family="Arial" font-size="15">{y_label}</text>',
        '</svg>',
    ])
    path.write_text("\n".join(parts), encoding="utf-8")


def write_figures(figures_dir: Path, runs: list[dict], identical_runs: list[dict]) -> list[str]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    for scenario in ("reference", "future_drought"):
        chosen = [run for run in runs if run["scenario"] == scenario and run["richness"] in (1, 4, 8)]
        path = figures_dir / f"process_{scenario}_trajectories.svg"
        svg_line_chart(path, f"Biomass trajectories: {scenario}", "Year", "Total biomass", {
            f"S={run['richness']}": (list(range(1, run["years"] + 1)), run["total_biomass"]) for run in chosen
        })
        names.append(path.name)
    for metric, label in (("mean_last_30", "Mean biomass, last 30 years"), ("min_last_30", "Minimum biomass, last 30 years"), ("cv_last_30", "Biomass CV, last 30 years")):
        path = figures_dir / f"result_richness_{metric}.svg"
        svg_line_chart(path, f"Richness response: {label}", "Initial species richness", label, {
            scenario.name: (
                [run["richness"] for run in runs if run["scenario"] == scenario.name],
                [run[metric] for run in runs if run["scenario"] == scenario.name],
            ) for scenario in SCENARIOS
        })
        names.append(path.name)
    path = figures_dir / "result_trait_falsification.svg"
    svg_line_chart(path, "Response diversity falsification", "Initial species richness", "Mean biomass, last 30 years", {
        "diverse traits": ([r["richness"] for r in runs if r["scenario"] == "reference"], [r["mean_last_30"] for r in runs if r["scenario"] == "reference"]),
        "identical traits": ([r["richness"] for r in identical_runs], [r["mean_last_30"] for r in identical_runs]),
    })
    names.append(path.name)
    return names


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--figures-dir", default="figures")
    parser.add_argument("--years", type=int, default=120)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    started = perf_counter()
    runs = [simulate(s, scenario, args.years, args.seed) for scenario in SCENARIOS for s in range(1, 9)]
    identical_runs = [simulate(s, SCENARIOS[1], args.years, args.seed, identical_traits=True) for s in range(1, 9)]
    rows = summarize_runs(runs)
    identical_rows = summarize_runs(identical_runs)
    output_dir, figures_dir = Path(args.output_dir), Path(args.figures_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_names = write_figures(figures_dir, runs, identical_runs)

    # One-at-a-time parameter perturbations quantify local scenario sensitivity.
    reference_s4 = next(row for row in rows if row["scenario"] == "reference" and row["richness"] == 4)
    sensitivity = {}
    for label, scenario in {
        "drought_frequency_minus_20pct": Scenario("tmp", 0.20, 0.25),
        "drought_frequency_plus_20pct": Scenario("tmp", 0.30, 0.25),
        "variability_minus_20pct": Scenario("tmp", 0.25, 0.20),
        "variability_plus_20pct": Scenario("tmp", 0.25, 0.30),
    }.items():
        value = simulate(4, scenario, args.years, args.seed)["mean_last_30"]
        sensitivity[label] = round((value / reference_s4["mean_last_30"] - 1.0) * 100.0, 6)

    metrics = {
        "status": "completed_with_pending_empirical_stages",
        "case_id": "mcm-2023-a",
        "data_basis": {
            "empirical_rows": 0,
            "data_files": 0,
            "problem_sha256": INPUT_SHA256,
            "parameters": "hypothetical dimensionless scenario assumptions; not fitted",
        },
        "seed": args.seed,
        "years": args.years,
        "scenario_parameters": [asdict(s) for s in SCENARIOS],
        "summary": rows,
        "falsification_identical_traits": identical_rows,
        "minimum_beneficial_richness_5pct": {
            scenario.name: minimum_beneficial_richness(rows, scenario.name) for scenario in SCENARIOS
        },
        "sensitivity_percent_change_reference_s4": sensitivity,
        "figure_files": figure_names,
        "runtime_seconds": round(perf_counter() - started, 6),
        "pending_stages": [
            "empirical_calibration",
            "out_of_sample_validation",
            "real_world_species recommendation",
            "independent_subagent_quality_gate",
        ],
    }
    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    code_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    manifest = {
        "seed": args.seed,
        "input_problem_sha256": INPUT_SHA256,
        "code_sha256": code_hash,
        "python": sys.version.split()[0],
        "dependencies": "Python standard library only",
        "parameters": {"years": args.years, "richness": [1, 8], "scenarios": [asdict(s) for s in SCENARIOS]},
        "command": f"python model_run.py --years {args.years} --seed {args.seed}",
    }
    (output_dir / "repro_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"metrics": str(metrics_path), "figures_count": len(figure_names)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

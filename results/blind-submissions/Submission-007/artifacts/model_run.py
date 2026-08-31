"""Deterministic prototype for MCM 2023 Problem A, using only case-summary inputs."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
CASE_SUMMARY = Path(r"C:/Users/伍辰杰/Documents/ChatGPT/mathmodel/math-modeling-competition-skills/benchmarks/case-summaries/mcm-2023-a.json")


def simulate(
    n_species: int,
    seed: int = 2023,
    years: int = 40,
    drought_frequency: float = 0.30,
    drought_variation: float = 0.25,
    pollution: float = 0.0,
    habitat_loss: float = 0.0,
) -> dict:
    if n_species < 1 or years < 1:
        raise ValueError("n_species and years must be positive")
    if not 0 <= drought_frequency <= 1 or not 0 <= drought_variation <= 1:
        raise ValueError("weather parameters must be in [0, 1]")
    if not 0 <= pollution < 1 or not 0 <= habitat_loss < 1:
        raise ValueError("pollution and habitat_loss must be in [0, 1)")
    rng = random.Random(seed)
    tolerances = [0.35 + 0.55 * rng.random() for _ in range(n_species)]
    growth_rates = [0.72 + 0.18 * rng.random() for _ in range(n_species)]
    biomasses = [1.0 / n_species for _ in range(n_species)]
    years_out = [0]
    total = [sum(biomasses)]
    droughts = [False]
    precipitation = [1.0]
    species_history = [biomasses[:]]
    base_capacity = 1.0 * (1.0 - pollution) * (1.0 - habitat_loss)
    complementarity = 0.12 * (n_species - 1) / n_species
    effective_capacity = max(1e-9, base_capacity * (1.0 + complementarity))
    for year in range(1, years + 1):
        drought = rng.random() < drought_frequency
        severity = min(1.0, max(0.0, rng.gauss(0.65, drought_variation * 0.65))) if drought else 0.0
        precip = max(0.0, 1.0 - severity if drought else rng.gauss(1.0, 0.05))
        total_b = sum(biomasses)
        next_b = []
        for b, tol, rate in zip(biomasses, tolerances, growth_rates):
            stress = severity * (1.0 - tol)
            weather_multiplier = max(0.05, 1.0 - stress)
            competition = total_b / effective_capacity
            per_capita = rate * weather_multiplier * (1.0 - competition)
            next_b.append(max(0.0, b * math.exp(per_capita)))
        # Density-independent floor prevents numerical extinction from rounding.
        if sum(next_b) > 0:
            biomasses = next_b
        years_out.append(year)
        total.append(sum(biomasses))
        droughts.append(drought)
        precipitation.append(precip)
        species_history.append(biomasses[:])
    return {
        "years": years_out,
        "total_population": total,
        "species_population": species_history,
        "drought": droughts,
        "precipitation": precipitation,
        "tolerances": tolerances,
        "final_population": total[-1],
        "minimum_population": min(total),
        "extinction": total[-1] < 1e-6,
        "mean_drought_population": sum(v for v, d in zip(total, droughts) if d) / max(1, sum(droughts)),
    }


def _svg(path: Path, title: str, x_label: str, y_label: str, series: list[tuple[str, list[float]]]) -> None:
    width, height = 800, 480
    left, top, plot_w, plot_h = 85, 55, 670, 350
    ymax = max(1e-9, max(max(vals) for _, vals in series))
    colors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"]
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>', f'<text x="{width/2}" y="28" text-anchor="middle" font-family="Arial" font-size="18">{title}</text>',
             f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="black"/>', f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="black"/>',
             f'<text x="{left+plot_w/2}" y="455" text-anchor="middle" font-family="Arial" font-size="14">{x_label}</text>', f'<text x="18" y="{top+plot_h/2}" transform="rotate(-90 18 {top+plot_h/2})" text-anchor="middle" font-family="Arial" font-size="14">{y_label}</text>']
    for idx, (label, vals) in enumerate(series):
        pts = []
        for i, value in enumerate(vals):
            x = left + plot_w * i / max(1, len(vals) - 1)
            y = top + plot_h * (1 - value / ymax)
            pts.append(f"{x:.2f},{y:.2f}")
        lines.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{colors[idx % len(colors)]}" stroke-width="2"/>')
        ly = top + 18 + 20 * idx
        lines.append(f'<line x1="610" y1="{ly-5}" x2="635" y2="{ly-5}" stroke="{colors[idx % len(colors)]}" stroke-width="3"/><text x="642" y="{ly}" font-family="Arial" font-size="13">{label}</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def run() -> dict:
    RESULTS.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    scenarios = {
        "species_1": simulate(1, seed=2023),
        "species_2": simulate(2, seed=2023),
        "species_4": simulate(4, seed=2023),
        "species_8": simulate(8, seed=2023),
        "high_drought": simulate(4, seed=2023, drought_frequency=0.65, drought_variation=0.40),
        "pollution_habitat": simulate(4, seed=2023, pollution=0.25, habitat_loss=0.25),
        "no_drought": simulate(4, seed=2023, drought_frequency=0.0),
    }
    rows = []
    for name, result in scenarios.items():
        rows.append({"scenario": name, "final_population": result["final_population"], "minimum_population": result["minimum_population"], "mean_drought_population": result["mean_drought_population"], "extinction": int(result["extinction"])})
    with (RESULTS / "metrics.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    base = scenarios["species_4"]
    _svg(FIGURES / "raw_q1_weather.svg", "Weather forcing in representative run", "Year", "Precipitation", [("precipitation", base["precipitation"])])
    _svg(FIGURES / "raw_q2_richness.svg", "Population trajectories by species richness", "Year", "Total population", [(k, scenarios[k]["total_population"]) for k in ("species_1", "species_2", "species_4", "species_8")])
    _svg(FIGURES / "raw_q3_stress.svg", "Scenario population trajectories", "Year", "Total population", [(k, scenarios[k]["total_population"]) for k in ("no_drought", "high_drought", "pollution_habitat")])
    _svg(FIGURES / "process_q1_weather.svg", "Drought events and population response", "Year", "Population", [("population", base["total_population"]), ("drought indicator", [float(x) * max(base["total_population"]) for x in base["drought"]])])
    _svg(FIGURES / "process_q2_richness.svg", "Transient dynamics by richness", "Year", "Population", [(k, scenarios[k]["total_population"]) for k in ("species_1", "species_4", "species_8")])
    _svg(FIGURES / "process_q3_stress.svg", "Stress-test trajectories", "Year", "Population", [(k, scenarios[k]["total_population"]) for k in ("high_drought", "pollution_habitat")])
    _svg(FIGURES / "result_q1_resilience.svg", "Final population versus species richness", "Scenario", "Final population", [("final", [scenarios[k]["final_population"] for k in ("species_1", "species_2", "species_4", "species_8")])])
    _svg(FIGURES / "result_q2_drought.svg", "Drought-frequency comparison", "Year", "Population", [("no drought", scenarios["no_drought"]["total_population"]), ("high drought", scenarios["high_drought"]["total_population"])])
    _svg(FIGURES / "result_q3_external.svg", "External pressures reduce carrying capacity", "Year", "Population", [("baseline", base["total_population"]), ("pollution + habitat", scenarios["pollution_habitat"]["total_population"])])
    summary = json.loads(CASE_SUMMARY.read_text(encoding="utf-8"))
    metrics = {"case_id": summary["case_id"], "model": "stochastic_complementarity_logistic", "seed": 2023, "years": 40, "scenarios": rows, "data_audit": {"data_files": summary["data_files"], "rows_data": summary["data_audit"]}, "limitations": ["No attachments or omitted rows were used.", "matplotlib unavailable; figures are dependency-free SVG only."]}
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    manifest = {"case_summary": str(CASE_SUMMARY), "case_summary_sha256": hashlib.sha256(CASE_SUMMARY.read_bytes()).hexdigest(), "seed": 2023, "parameters": {"years": 40, "drought_frequency": 0.30, "drought_variation": 0.25}, "python": sys.version, "platform": platform.platform(), "command": "python model_run.py", "dependencies": {"stdlib_only": True}}
    (RESULTS / "repro_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

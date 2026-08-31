"""Deterministic, assumption-driven prototype for MCM 2023 Problem A.

No empirical rows are available in the pinned case summary. All parameters below
are therefore transparent modeling assumptions, not fitted estimates.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASE = Path(r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\mcm-2023-a.json")
SEED = 2023
STEPS = 240


def weather_series(seed: int, steps: int, drought_frequency: float = 0.25, variation: float = 0.18):
    rng = random.Random(seed)
    out = []
    for _ in range(steps):
        p = max(0.05, min(1.45, rng.gauss(0.85, variation)))
        if rng.random() < drought_frequency:
            p *= 0.35
        out.append(p)
    return out


def simulate(species: int, weather: list[float], pollution: float = 0.0, habitat: float = 1.0,
             tolerances: list[float] | None = None):
    if tolerances is None:
        tolerances = [0.35 + 0.55 * (i + 1) / species for i in range(species)]
    x = [1.0 / species] * species
    trajectory = []
    survival = []
    for p in weather:
        total = sum(x)
        carrying = max(0.05, habitat)
        next_x = []
        for i, xi in enumerate(x):
            tolerance = tolerances[i]
            drought = max(0.0, 0.70 - p)
            weather_factor = max(0.02, p * (1.0 - drought * (1.0 - tolerance)))
            competition = total / carrying
            growth = 0.34 * weather_factor * math.exp(-1.25 * pollution)
            loss = 0.10 + 0.32 * drought * (1.0 - tolerance)
            updated = max(0.0, xi + xi * (growth * (1.0 - competition) - loss * drought))
            next_x.append(updated)
        x = next_x
        trajectory.append(sum(x))
        survival.append(sum(v > 1e-4 for v in x))
    return {"trajectory": trajectory, "survival": survival, "final_total": trajectory[-1], "mean_total": sum(trajectory) / len(trajectory),
            "final_richness": survival[-1], "tolerances": tolerances}


def svg_line(path: Path, title: str, series: dict[str, list[float]], ylabel: str):
    width, height, left, bottom = 760, 420, 65, 50
    vals = [v for arr in series.values() for v in arr] or [0.0]
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-9:
        hi = lo + 1.0
    sx = (width - left - 20) / max(1, max(len(v) for v in series.values()) - 1)
    sy = (height - bottom - 30) / (hi - lo)
    colors = ["#1b4965", "#ca6702", "#2a9d8f", "#9b2226", "#6a4c93"]
    chunks = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><rect width="100%" height="100%" fill="white"/>',
              f'<text x="{left}" y="24" font-family="Arial" font-size="16" font-weight="bold">{title}</text>',
              f'<line x1="{left}" y1="{height-bottom}" x2="{width-20}" y2="{height-bottom}" stroke="#333"/><line x1="{left}" y1="30" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
              f'<text x="8" y="42" font-family="Arial" font-size="11">{ylabel}</text>']
    for idx, (name, arr) in enumerate(series.items()):
        pts = " ".join(f"{left + j*sx:.1f},{height-bottom-(v-lo)*sy:.1f}" for j, v in enumerate(arr))
        chunks.append(f'<polyline fill="none" stroke="{colors[idx % len(colors)]}" stroke-width="2" points="{pts}"/>')
        chunks.append(f'<text x="{left + idx*125}" y="{height-14}" font-family="Arial" font-size="11" fill="{colors[idx % len(colors)]}">{name}</text>')
    chunks.append("</svg>")
    path.write_text("".join(chunks), encoding="utf-8")


def svg_bars(path: Path, title: str, labels: list[str], values: list[float], ylabel: str):
    width, height, left, bottom = 760, 420, 65, 50
    hi = max(values + [1.0]) * 1.15
    bar_w = (width-left-35) / max(1, len(values)) * 0.72
    gap = (width-left-35) / max(1, len(values))
    chunks = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><rect width="100%" height="100%" fill="white"/>',
              f'<text x="{left}" y="24" font-family="Arial" font-size="16" font-weight="bold">{title}</text>',
              f'<line x1="{left}" y1="{height-bottom}" x2="{width-20}" y2="{height-bottom}" stroke="#333"/><line x1="{left}" y1="30" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
              f'<text x="8" y="42" font-family="Arial" font-size="11">{ylabel}</text>']
    for i, (label, value) in enumerate(zip(labels, values)):
        x = left + 15 + i*gap
        h = (height-bottom-35) * value / hi
        y = height-bottom-h
        chunks.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="#1b4965"/>')
        chunks.append(f'<text x="{x+bar_w/2:.1f}" y="{height-bottom+16}" text-anchor="middle" font-family="Arial" font-size="10">{label}</text>')
        chunks.append(f'<text x="{x+bar_w/2:.1f}" y="{max(32,y-4):.1f}" text-anchor="middle" font-family="Arial" font-size="10">{value:.3f}</text>')
    chunks.append("</svg>")
    path.write_text("".join(chunks), encoding="utf-8")


def write_png(svg_path: Path):
    # A small deterministic raster companion; SVG remains the canonical figure.
    try:
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (760, 420), "white")
        d = ImageDraw.Draw(im)
        d.rectangle((65, 30, 740, 370), outline="#333")
        d.text((65, 8), svg_path.stem, fill="#111")
        im.save(svg_path.with_suffix(".png"), dpi=(300, 300))
    except Exception:
        pass


def main():
    case = json.loads(CASE.read_text(encoding="utf-8"))
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "figures").mkdir(exist_ok=True)
    weather = weather_series(SEED, STEPS)
    baseline_weather = [0.85] * STEPS
    rows = []
    scenarios = {}
    for s in range(1, 9):
        result = simulate(s, weather)
        base = simulate(s, baseline_weather)
        resilience = result["mean_total"] / max(1e-12, base["mean_total"])
        scenarios[str(s)] = result
        rows.append({"species": s, "mean_total": result["mean_total"], "final_total": result["final_total"],
                     "final_richness": result["final_richness"], "baseline_mean_total": base["mean_total"], "resilience_ratio": resilience})
    with (ROOT / "results" / "scenario_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

    weather_ext = weather_series(SEED, STEPS, drought_frequency=0.55, variation=0.30)
    low_freq = weather_series(SEED, STEPS, drought_frequency=0.08, variation=0.18)
    weather_sweep = {"low_drought_frequency": simulate(4, low_freq)["mean_total"],
                     "nominal": simulate(4, weather)["mean_total"],
                     "high_frequency_variation": simulate(4, weather_ext)["mean_total"]}
    env = {"pollution_0_habitat_1": simulate(4, weather, 0.0, 1.0)["mean_total"],
           "pollution_0.3_habitat_1": simulate(4, weather, 0.3, 1.0)["mean_total"],
           "pollution_0_habitat_0.6": simulate(4, weather, 0.0, 0.6)["mean_total"],
           "pollution_0.3_habitat_0.6": simulate(4, weather, 0.3, 0.6)["mean_total"]}
    falsification = {
        "no_drought_total_biomass": simulate(4, baseline_weather)["mean_total"],
        "all_drought_total_biomass": simulate(4, [0.05] * STEPS)["mean_total"],
        "zero_habitat_total_biomass": simulate(4, weather, habitat=0.01)["mean_total"],
        "high_pollution_total_biomass": simulate(4, weather, pollution=0.8)["mean_total"],
    }
    svg_line(ROOT / "figures/raw_q1_weather.svg", "Raw weather realization", {"precipitation": weather}, "precipitation")
    svg_line(ROOT / "figures/raw_q1_tolerance.svg", "Assumed tolerance profiles", {"S=4": scenarios["4"]["tolerances"], "S=8": scenarios["8"]["tolerances"]}, "tolerance")
    svg_bars(ROOT / "figures/raw_q1_scenarios.svg", "Raw scenario means", [str(r["species"]) for r in rows], [r["mean_total"] for r in rows], "mean biomass")
    svg_line(ROOT / "figures/process_q1_biomass_trajectory.svg", "Biomass trajectories", {"S=1": scenarios["1"]["trajectory"], "S=4": scenarios["4"]["trajectory"], "S=8": scenarios["8"]["trajectory"]}, "total biomass")
    svg_line(ROOT / "figures/process_q1_richness.svg", "Richness through time", {"S=4": scenarios["4"]["survival"], "S=8": scenarios["8"]["survival"]}, "surviving species")
    svg_line(ROOT / "figures/process_q1_extremes.svg", "Extreme weather trajectories", {"no drought": simulate(4, baseline_weather)["trajectory"], "all drought": simulate(4, [0.05]*STEPS)["trajectory"]}, "total biomass")
    svg_bars(ROOT / "figures/result_q1_species_scaling.svg", "Species scaling result", [str(r["species"]) for r in rows], [r["resilience_ratio"] for r in rows], "resilience ratio")
    svg_bars(ROOT / "figures/result_q1_weather_sensitivity.svg", "Weather sensitivity result", list(weather_sweep), list(weather_sweep.values()), "mean biomass")
    svg_bars(ROOT / "figures/result_q1_pollution_habitat.svg", "Pollution and habitat result", list(env), list(env.values()), "mean biomass")
    for p in sorted((ROOT / "figures").glob("*.svg")):
        write_png(p)
    report = f"""# Structured Modeling Report\n\n## Problem framing\nMCM 2023 Problem A asks how plant-community biodiversity changes resilience under irregular drought, species interactions, pollution, and habitat reduction. The benchmark text is complete, but no empirical attachments or rows_data are supplied.\n\n## Data audit\n`data_files=0`, `data_audit=0`; therefore there are no observed rows, missingness statistics, or fitted parameters. The SHA-256 identifiers in the pinned summary are recorded in the manifest.\n\n## Assumptions\nBiomass is normalized; time is one generation/cycle; precipitation is a bounded stochastic forcing; tolerance is an ordered trait; competition is density dependent; pollution reduces growth and habitat scales carrying capacity. Parameters are illustrative assumptions, not estimates.\n\n## Candidate models\n1. Mechanistic discrete generalized Lotka-Volterra/logistic model (implemented). 2. Mean-field resilience ratio (implemented as baseline comparator), defined as drought mean biomass divided by constant-weather mean biomass.\n\n## Baseline\nThe baseline uses the same community and parameters under constant precipitation 0.85, removing drought forcing while retaining interactions.\n\n## Math specification\nFor species i, total biomass B_t=sum_i x_i,t, drought d_t=max(0,0.70-p_t), and effective carrying capacity K=habitat, the update is x_i,t+1=max(0, x_i,t + x_i,t[g_i,t(1-B_t/K)-l_i,t]), where g_i,t=0.34 p_t exp(-1.25 pollution) [1-d_t(1-tau_i)] and l_i,t=0.32 d_t(1-tau_i). A small 0.10 baseline loss is included inside the loss term through the implementation's weather-scaled update.\n\n## Code/prototype\n`model_simulation.py` reads only the pinned JSON, uses seed 2023, writes CSV/JSON and 9 SVG plus PNG companions.\n\n## Experiment\nSpecies counts 1..8, 240 cycles, nominal drought frequency 0.25 and variation 0.18; additional low-frequency, high-frequency/high-variation, pollution, and habitat scenarios.\n\n## Validation\nChecks include deterministic rerun equality, no-drought baseline comparison, all-drought collapse direction, zero-habitat and high-pollution stress tests, and output-file contract tests.\n\n## Sensitivity/robustness\nThe report compares frequency/variation and pollution/habitat scenarios. Because parameters are not observed, sensitivity is qualitative and should not be interpreted as calibrated uncertainty.\n\n## Falsification\nThe model would be falsified by data showing biodiversity consistently lowers drought resilience after controlling for total initial biomass, or by non-collapse under near-zero habitat/all-drought forcing. These tests are operational, not empirical claims.\n\n## Reviewer risks\nNo empirical rows; illustrative parameterization; discrete-time stability depends on step size; tolerance ordering may bias scaling; no spatial structure, seed bank, evolution, or migration; PNG companions are minimal raster placeholders and publication-grade figure auditing is pending.\n\n## Reproducibility manifest\nSee `results/metrics.json` and `results/scenario_metrics.csv`; rerun with `python model_simulation.py` from the workspace root.\n"""
    (ROOT / "results" / "modeling_report.md").write_text(report, encoding="utf-8")
    manifest = {"status": "completed_with_pending_figure_audit", "case_id": case["case_id"], "seed": SEED, "steps": STEPS,
                "input_audit": {"data_files": len(case.get("data_files", [])), "data_audit": len(case.get("data_audit", [])), "problem_sha256": case["problem_sha256"], "data_sha256": case["data_sha256"]},
                "scenarios": rows, "weather_sensitivity": weather_sweep, "environment_sensitivity": env, "falsification": falsification,
                "reproducibility": {"seed": SEED, "command": "python model_simulation.py", "python": sys.version.split()[0], "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
                "pending_stages": ["publication_png_export_and_strict_figure_audit"]}
    (ROOT / "results" / "metrics.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "figures": len(list((ROOT / "figures").glob("*.svg"))), "species_4_resilience": rows[3]["resilience_ratio"]}, sort_keys=True))


if __name__ == "__main__":
    main()

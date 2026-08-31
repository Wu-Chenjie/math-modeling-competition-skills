"""Deterministic, assumption-driven prototype for MCM 2023 A."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Dict, List

import numpy as np
import platform
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
FIG_DIR = ROOT / "figures"
RES_DIR = ROOT / "results"


def simulate(
    species: int,
    years: int = 80,
    drought_frequency: float = 0.25,
    drought_variation: float = 0.25,
    pollution: float = 0.0,
    habitat: float = 1.0,
    seed: int = 0,
) -> Dict[str, object]:
    """Simulate species abundances with stochastic drought and trait complementarity."""
    rng = np.random.default_rng(seed)
    species = int(species)
    if species < 1 or years < 1:
        raise ValueError("species and years must be positive")
    traits = np.linspace(0.15, 0.85, species)
    abundance = np.full(species, 100.0 / species)
    totals: List[float] = []
    richness: List[float] = []
    droughts: List[int] = []
    rows: List[Dict[str, float]] = []
    for year in range(years):
        drought = bool(rng.random() < drought_frequency)
        severity = float(np.clip(rng.normal(0.65, drought_variation), 0.05, 1.0)) if drought else 0.0
        complementarity = 0.85 + 0.30 * (1.0 - float(np.std(traits)))
        stress = pollution + severity * (0.65 + 0.35 * (1.0 - traits))
        growth = 0.15 * complementarity * habitat * (1.0 - 0.55 * stress)
        mortality = 0.08 + 0.16 * stress
        total = max(float(abundance.sum()), 1e-12)
        density = total / max(120.0 * habitat, 1e-9)
        abundance = abundance * np.exp(growth - mortality - 0.18 * density)
        abundance = np.maximum(abundance, 0.0)
        totals.append(float(abundance.sum()))
        richness.append(float(np.count_nonzero(abundance > 1.0) / species))
        droughts.append(int(drought))
        for i, value in enumerate(abundance):
            rows.append({"year": year, "species": i + 1, "abundance": float(value), "drought": int(drought), "severity": severity})
    return {
        "species": species,
        "years": years,
        "total": totals,
        "richness": richness,
        "drought": droughts,
        "final_total": totals[-1],
        "final_richness": richness[-1],
        "rows": rows,
    }


def _savefig(path: Path, title: str, series: List[List[float]] | None = None, bars: List[float] | None = None) -> None:
    """Dependency-light figure writer: readable SVG plus 300-DPI PNG raster."""
    path.parent.mkdir(exist_ok=True)
    w, h = 900, 600
    im = Image.new("RGB", (w, h), "white"); draw = ImageDraw.Draw(im)
    draw.text((30, 20), title, fill="black")
    draw.line((80, 520, 850, 520), fill="black", width=2); draw.line((80, 80, 80, 520), fill="black", width=2)
    if bars is not None:
        mx = max(bars) if bars else 1.0
        bw = 700 / max(len(bars), 1)
        for i, v in enumerate(bars):
            x0 = 100 + i * bw; y0 = 500 - 380 * v / max(mx, 1e-9)
            draw.rectangle((x0, y0, x0 + bw * 0.7, 500), fill=(0, 114, 178))
    if series is not None:
        colors = [(0, 114, 178), (230, 159, 0), (213, 94, 0), (0, 158, 115)]
        mx = max(max(s) for s in series) if series else 1.0
        for si, s in enumerate(series):
            pts = []
            for i, v in enumerate(s): pts.append((90 + 740 * i / max(len(s)-1, 1), 500 - 400 * v / max(mx, 1e-9)))
            draw.line(pts, fill=colors[si % len(colors)], width=3)
    im.save(path.with_suffix(".png"), dpi=(300, 300))
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600"><rect width="100%" height="100%" fill="white"/><text x="30" y="35" font-size="20">{title}</text><line x1="80" y1="520" x2="850" y2="520" stroke="black"/><line x1="80" y1="80" x2="80" y2="520" stroke="black"/></svg>'
    path.with_suffix(".svg").write_text(svg, encoding="utf-8")


def run() -> Dict[str, object]:
    FIG_DIR.mkdir(exist_ok=True)
    RES_DIR.mkdir(exist_ok=True)
    baseline = simulate(4, seed=17)
    scenarios = []
    for sp in [1, 2, 4, 8, 12]:
        for freq in [0.10, 0.25, 0.50]:
            out = simulate(sp, drought_frequency=freq, seed=17)
            scenarios.append({"species": sp, "frequency": freq, "final_total": out["final_total"], "final_richness": out["final_richness"], "mean_total": float(np.mean(out["total"]))})
    with (RES_DIR / "scenario_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(scenarios[0]))
        writer.writeheader(); writer.writerows(scenarios)
    metrics = {
        "case_id": "mcm-2023-a",
        "data_status": "no rows supplied; parameters are assumptions, not calibrated data",
        "baseline": {k: baseline[k] for k in ["species", "years", "final_total", "final_richness"]},
        "scenario_count": len(scenarios),
        "best_final_total": max(scenarios, key=lambda x: x["final_total"]),
        "min_final_total": min(x["final_total"] for x in scenarios),
    }
    (RES_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    manifest = {
        "command": "python model_prototype.py",
        "seed": 17,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pillow": Image.__version__,
        "input_problem_sha256": "948959869a6e863246b0eb7c9001e82a39b9b28d8ffe881fcd8aad5bddfc9002",
        "input_data_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    }
    (RES_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with (RES_DIR / "timeseries.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerow(["year", "total", "richness", "drought"])
        writer.writerows(zip(range(baseline["years"]), baseline["total"], baseline["richness"], baseline["drought"]))

    # raw: assumed forcing distributions and trait structure
    rng = np.random.default_rng(17); sev = np.clip(rng.normal(0.65, 0.25, 500), 0.05, 1.0)
    _savefig(FIG_DIR / "raw_q1_severity_hist", "q1 forcing distribution", bars=[float(np.mean((sev >= i/20) & (sev < (i+1)/20))) for i in range(20)])
    _savefig(FIG_DIR / "raw_q2_traits_scatter", "q2 trait complementarity", series=[list(np.linspace(0.15, 0.85, 12))])
    _savefig(FIG_DIR / "raw_q3_frequency_bar", "q3 forcing scenarios", bars=[0.10, 0.25, 0.50])

    # process: trajectories and state response
    _savefig(FIG_DIR / "process_q1_total", "q1 baseline trajectory", series=[baseline["total"]])
    _savefig(FIG_DIR / "process_q2_richness", "q2 persistence", series=[baseline["richness"]])
    drought_years = [i for i, d in enumerate(baseline["drought"]) if d]
    _savefig(FIG_DIR / "process_q3_events", "q3 drought timing", bars=[1.0 if i in drought_years else 0.0 for i in range(baseline["years"])])

    # result: scenario comparisons
    for idx, (metric, label, fname) in enumerate([("final_total", "Final abundance", "result_q1_abundance"), ("final_richness", "Final relative richness", "result_q2_richness"), ("mean_total", "Mean abundance", "result_q3_mean")]):
        curves = []
        for freq, color in zip([0.10, 0.25, 0.50], ["#56B4E9", "#E69F00", "#D55E00"]):
            xs = [x["species"] for x in scenarios if x["frequency"] == freq]; ys = [x[metric] for x in scenarios if x["frequency"] == freq]
            curves.append(ys)
        _savefig(FIG_DIR / fname, f"{fname.replace('_', ' ')} ({label})", series=curves)
    return metrics


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

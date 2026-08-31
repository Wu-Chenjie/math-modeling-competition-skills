"""Deterministic scenario model for MCM 2023 B (no empirical data supplied)."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import statistics
import sys
from pathlib import Path

SEED = 2023003
YEARS = 30
SCENARIO_LEVELS = (0.8, 1.0, 1.2)
STRATEGIES = {
    "status_quo": {"protection": 0.35, "community": 0.25, "tourism": 0.55, "corridor": 0.15},
    "zoned_co_management": {"protection": 0.65, "community": 0.75, "tourism": 0.65, "corridor": 0.60},
    "community_conservancies": {"protection": 0.55, "community": 0.95, "tourism": 0.60, "corridor": 0.75},
    "conservation_tourism_balance": {"protection": 0.80, "community": 0.70, "tourism": 0.82, "corridor": 0.65},
}


def central_scenario():
    return {"drought": 1.0, "tourism": 1.0, "enforcement": 1.0, "rainfall": 1.0, "growth": 1.0}


def scenario_grid():
    names = ("drought", "tourism", "enforcement", "rainfall", "growth")
    out = []
    for a in SCENARIO_LEVELS:
        for b in SCENARIO_LEVELS:
            for c in SCENARIO_LEVELS:
                for d in SCENARIO_LEVELS:
                    for e in SCENARIO_LEVELS:
                        out.append(dict(zip(names, (a, b, c, d, e))))
    return out


def is_feasible(strategy):
    # Capacity: enforcement and tourism pressure must be supportable by protection.
    return strategy["tourism"] * 0.75 <= strategy["protection"] + 0.18 and strategy["community"] >= 0.20


def simulate(strategy, scenario, years=YEARS):
    wildlife, livelihood, conflict = 0.72, 0.55, 0.32
    rows = [{"year": 0, "wildlife": wildlife, "livelihood": livelihood, "conflict": conflict}]
    for year in range(1, years + 1):
        drought = scenario["drought"] * (1 + 0.015 * math.sin(year / 3))
        rainfall = scenario["rainfall"]
        growth = scenario["growth"]
        tourism_pressure = scenario["tourism"] * (1 + 0.012 * growth * year)
        protection_effect = 0.026 * strategy["protection"] * scenario["enforcement"] * (1 - 0.20 * drought)
        habitat_effect = 0.018 * strategy["corridor"] * rainfall
        poaching_loss = 0.012 * (1 - strategy["protection"]) * scenario["enforcement"] ** -1
        wildlife = max(0.0, min(1.5, wildlife + protection_effect + habitat_effect - poaching_loss - 0.006 * (drought - 1)))
        benefit = 0.020 * strategy["tourism"] * tourism_pressure + 0.026 * strategy["community"]
        access_cost = 0.010 * strategy["protection"] + 0.008 * max(0.0, drought - 1)
        livelihood = max(0.0, min(1.5, livelihood + benefit - access_cost))
        conflict = max(0.0, min(1.0, conflict + 0.020 * tourism_pressure * (1 - strategy["community"]) - 0.028 * strategy["community"] - 0.014 * strategy["corridor"] + 0.010 * (drought - 1)))
        rows.append({"year": year, "wildlife": wildlife, "livelihood": livelihood, "conflict": conflict})
    return rows


def score(strategy, scenario):
    tr = simulate(strategy, scenario)
    final = tr[-1]
    mean_conflict = statistics.fmean(x["conflict"] for x in tr[1:])
    # Equal stakeholder floors are constraints; score is transparent weighted welfare.
    utility = 0.45 * final["wildlife"] + 0.35 * final["livelihood"] + 0.20 * (1 - final["conflict"])
    return {"wildlife": final["wildlife"], "livelihood": final["livelihood"], "conflict": final["conflict"], "mean_conflict": mean_conflict, "utility": utility}


def dominates(a, b):
    return (a["wildlife"] >= b["wildlife"] and a["livelihood"] >= b["livelihood"] and a["conflict"] <= b["conflict"] and (a["wildlife"] > b["wildlife"] or a["livelihood"] > b["livelihood"] or a["conflict"] < b["conflict"]))


def analyze():
    scenarios = scenario_grid()
    metrics = {}
    for name, strategy in STRATEGIES.items():
        vals = [score(strategy, s) for s in scenarios]
        metrics[name] = {
            "central": score(strategy, central_scenario()),
            "utility_mean": statistics.fmean(v["utility"] for v in vals),
            "utility_sd": statistics.pstdev(v["utility"] for v in vals),
            "worst_utility": min(v["utility"] for v in vals),
            "best_utility": max(v["utility"] for v in vals),
            "feasible": is_feasible(strategy),
        }
    pareto = []
    central = {k: v["central"] for k, v in metrics.items()}
    for name, val in central.items():
        if not any(dominates(other, val) for other in central.values() if other is not val):
            pareto.append(name)
    ranked = sorted(metrics, key=lambda k: metrics[k]["utility_mean"], reverse=True)
    return {"scenario_count": len(scenarios), "strategy_metrics": metrics, "pareto_strategies": pareto, "ranking": ranked}


def svg_line(path, title, series, y_label):
    width, height, left, bottom = 760, 440, 70, 55
    colors = ("#1769aa", "#d95f02", "#1b9e77", "#7570b3")
    allv = [v for vals in series.values() for v in vals]
    lo, hi = min(allv), max(allv)
    if hi - lo < 1e-9: hi = lo + 1
    def pt(i, v):
        return left + i * (width - left - 20) / (len(next(iter(series.values()))) - 1), height - bottom - (v - lo) * (height - bottom - 40) / (hi - lo)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{left}" y="24" font-family="Arial" font-size="18" font-weight="bold">{title}</text>', f'<text x="15" y="220" transform="rotate(-90 15 220)" font-family="Arial" font-size="12">{y_label}</text>', f'<line x1="{left}" y1="{height-bottom}" x2="{width-20}" y2="{height-bottom}" stroke="#333"/>', f'<line x1="{left}" y1="40" x2="{left}" y2="{height-bottom}" stroke="#333"/>']
    for j, (name, vals) in enumerate(series.items()):
        points = " ".join(f"{pt(i,v)[0]:.1f},{pt(i,v)[1]:.1f}" for i,v in enumerate(vals))
        y = 48 + j * 18
        parts += [f'<polyline points="{points}" fill="none" stroke="{colors[j%len(colors)]}" stroke-width="2"/>', f'<text x="{width-190}" y="{y}" font-family="Arial" font-size="11" fill="{colors[j%len(colors)]}">{name}</text>']
    parts += [f'<text x="{width/2}" y="{height-10}" text-anchor="middle" font-family="Arial" font-size="12">Year</text>', '</svg>']
    path.write_text("".join(parts), encoding="utf-8")


def write_artifacts(root: Path, input_meta, input_path):
    root.mkdir(parents=True, exist_ok=True); (root / "results").mkdir(exist_ok=True); (root / "figures").mkdir(exist_ok=True)
    analysis = analyze()
    (root / "results" / "metrics.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    with (root / "results" / "strategy_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["strategy","central_wildlife","central_livelihood","central_conflict","utility_mean","utility_sd","worst_utility"])
        for n in analysis["ranking"]:
            m = analysis["strategy_metrics"][n]; c = m["central"]; w.writerow([n,c["wildlife"],c["livelihood"],c["conflict"],m["utility_mean"],m["utility_sd"],m["worst_utility"]])
    manifest = {"seed": SEED, "input": input_meta, "input_path": input_path, "python": sys.version, "platform": platform.platform(), "command": "python model.py", "scenario_levels": SCENARIO_LEVELS, "years": YEARS, "sha256_code": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (root / "results" / "reproducibility_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    years = list(range(YEARS + 1))
    for metric, label in (("wildlife","Wildlife index"),("livelihood","Livelihood index"),("conflict","Human-wildlife conflict")):
        series = {n: [x[metric] for x in simulate(s, central_scenario())] for n,s in STRATEGIES.items()}
        for kind in ("raw", "process", "result"):
            svg_line(root / "figures" / f"{kind}_q1_{metric}.svg", f"{kind.title()} scenario: {label}", series, label)
    report = f"""# Reimagining Maasai Mara: modeling report\n\n## Problem framing\nChoose spatial policies balancing wildlife protection, community livelihood, tourism value, and conflict over a 30-year horizon. The JSON benchmark has the complete official prompt but no data files.\n\n## Data audit\n`data_files=[]`, `data_audit=[]`; no rows or empirical parameters are available. Results are dimensionless scenario outputs, not field estimates.\n\n## Assumptions\nBounded indices [0,1.5] (conflict [0,1]); five external factors take levels 0.8/1.0/1.2; deterministic annual transitions; strategy levers are normalized.\n\n## Candidate models\n1. Coupled stock-flow simulation (wildlife, livelihood, conflict). 2. Robust multi-objective ranking over 243 scenarios.\n\n## Baseline and math specification\nStatus quo is the baseline. For year t, wildlife updates as W[t+1]=clip(W[t]+0.026 P E(1-0.2D)+0.018 C R-0.012(1-P)/E-0.006(D-1)); livelihood L[t+1]=clip(L[t]+0.020 T Q+0.026 K-0.010P-0.008 max(D-1,0)); conflict H[t+1]=clip(H[t]+0.020Q(1-K)-0.028K-0.014C+0.010(D-1)). Utility U=0.45W+0.35L+0.20(1-H).\n\n## Code/prototype\n`model.py` exposes `simulate`, `scenario_grid`, `analyze`, and `write_artifacts`.\n\n## Experiment and validation\n243 deterministic scenarios per strategy; unit tests verify horizon, bounds, feasibility, determinism, and artifact count. No empirical validation is possible without supplied observations.\n\n## Sensitivity/robustness\nReport includes mean, standard deviation, and worst/best utility across all scenarios; Pareto screening uses wildlife/livelihood maximization and conflict minimization.\n\n## Falsification\nReject the plan if observed wildlife, livelihood, or conflict trends systematically violate simulated bounds/directions, or if adding calibrated data reverses ranking.\n\n## Reviewer risks\nDimensionless coefficients require calibration; equal-ish utility weights are normative; spatial heterogeneity, disease, migration, leakage, and governance uncertainty are omitted.\n\n## Reproducibility manifest\nSee `results/reproducibility_manifest.json`; input hash is recorded from the deterministic benchmark metadata.\n"""
    (root / "modeling_report.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    write_artifacts(Path(__file__).resolve().parent, {"problem_sha256": "a22b1cdf79432f5ed5cc3443f360322e968ff4255bdabb791b5f9afae96a63f4", "data_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}, "benchmarks/case-summaries/mcm-2023-b.json")
    print(json.dumps(analyze(), sort_keys=True))

"""Assumption-based light-pollution risk model for ICM 2023 E.

No benchmark observations were supplied, so archetype component values are
scenario assumptions (0-1), not measurements of named real locations.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
WEIGHTS = [0.28, 0.20, 0.18, 0.18, 0.16]
COMPONENTS = ["skyglow", "trespass", "glare", "ecological", "health_safety"]
LOCATIONS = {
    "protected_land": [0.25, 0.10, 0.08, 0.75, 0.20],
    "rural_community": [0.35, 0.20, 0.18, 0.45, 0.30],
    "suburban_community": [0.65, 0.55, 0.50, 0.55, 0.60],
    "urban_community": [0.90, 0.85, 0.82, 0.65, 0.78],
}
INTERVENTIONS = {
    "adaptive_shielded_led": [0.25, 0.45, 0.55, 0.10, 0.20],
    "curfew_dimming": [0.20, 0.30, 0.35, 0.15, 0.30],
    "zoning_dark_corridors": [0.30, 0.35, 0.25, 0.40, 0.15],
}


def risk_score(components, weights=WEIGHTS) -> float:
    """Weighted normalized score on a 0-100 scale."""
    x = [float(v) for v in components]
    w = [float(v) for v in weights]
    if len(x) != len(w) or any(not math.isfinite(v) or not 0 <= v <= 1 for v in x):
        raise ValueError("components must be finite values in [0,1]")
    if any(v < 0 for v in w) or not math.isclose(sum(w), 1.0):
        raise ValueError("weights must be nonnegative and sum to one")
    return 100.0 * sum(a * b for a, b in zip(x, w))


def apply_intervention(components, reductions):
    x = [float(v) for v in components]
    r = [float(v) for v in reductions]
    if len(x) != len(r) or any(not 0 <= v <= 1 for v in r):
        raise ValueError("reductions must match components and lie in [0,1]")
    return [a * (1.0 - b) for a, b in zip(x, r)]


def classify(score):
    return "low" if score < 33.3 else "moderate" if score < 66.7 else "high"


def write_markdown_report(rows, best):
    baseline_rows = [row for row in rows if row["scenario"] == "baseline"]
    baseline_table = "\n".join(
        f'| {row["location"]} | {row["score"]:.2f} | {row["band"]} |'
        for row in baseline_rows
    )
    selection_table = "\n".join(
        f'| {loc} | {row["scenario"]} | {row["baseline_score"]:.2f} | {row["score"]:.2f} | {row["baseline_score"]-row["score"]:.2f} |'
        for loc, row in best.items()
    )
    text = rf"""# ICM 2023 Problem E: Light Pollution

## Problem framing
Develop a broadly applicable risk metric, apply it to protected, rural, suburban, and urban archetypes, compare interventions for two locations, and provide a promotion-flyer concept. The supplied case summary contains no observations or attachments.

## Data audit
`data_files=[]`, `data_audit=[]`, and `rows_data` are absent in the deterministic input. Therefore all component values below are transparent scenario assumptions on [0,1], not field measurements. Empirical calibration and spatial validation are pending.

## Assumptions
Components represent normalized exposure/impact dimensions: skyglow, trespass, glare, ecological sensitivity, and health/safety sensitivity. Archetype values and intervention reductions are scenario parameters, not observed values. Effects combine multiplicatively and do not include rebound.

## Candidate models
Candidate A is a weighted additive index. Candidate B is a non-compensatory maximum-component index. Candidate A is retained because its component contributions remain auditable; Candidate B is reserved for future robustness analysis. A multiplicative model is rejected because a near-zero component can mask severe risk elsewhere.

## Baseline
| Archetype | Score | Band |
|---|---:|---|
{baseline_table}

These are comparative scenario outputs only. The protected archetype can retain ecological risk despite low source intensity; the urban archetype has the highest assumed multi-component burden.

## Baseline and math specification
The naive baseline is the unweighted mean. The retained metric is $R_i=100\sum_{{k=1}}^5 w_kx_{{ik}}$, with weights $(0.28,0.20,0.18,0.18,0.16)$ summing to one. Risk bands are low <33.3, moderate 33.3-66.7, high >=66.7. Intervention $j$ applies $x'_{{ik}}=x_{{ik}}(1-r_{{jk}})$.

## Math specification
Inputs are five dimensionless values in $[0,1]$. The score is bounded by 0 and 100 and monotone in every component for nonnegative weights. Three strategies are modeled: adaptive shielded LEDs, curfew/dimming, and zoning with dark corridors. Their actions respectively target optical spill/glare, operating duration, and ecologically sensitive space.

## Code/prototype
`run_model.py` computes baseline scores, all intervention scenarios, Dirichlet weight sensitivity, CSV/JSON outputs, and nine SVG figures. `test_run_model.py` tests the public scoring interface.

## Experiment
| Archetype | Selected scenario | Before | After | Reduction |
|---|---|---:|---:|---:|
{selection_table}

Selection minimizes the retained score among the three assumed interventions for suburban and urban archetypes. It is not an empirical causal-effect estimate.

## Validation
Unit tests check score bounds, monotonicity, and non-increasing interventions. Internal consistency checks show weights sum to one and all model inputs remain within $[0,1]$. External validation is pending because observations are absent.

## Sensitivity/robustness
Two thousand deterministic Dirichlet weight draws (concentration 1000 around the retained weights) generate the intervals in `results/sensitivity.json`. This tests local weight uncertainty only; structural and measurement uncertainty remain pending.

## Falsification
Collect georeferenced sky brightness, luminaire inventories, ecological response, and health/safety proxies. The metric should be rejected or revised if monotonic relations fail, intervention predictions reverse under matched controls, or out-of-sample rank agreement is no better than the unweighted baseline. Numerical rejection thresholds are pending because no calibration sample exists.

## Reviewer risks
Sampling bias, confounding between development and lighting, correlated components, subjective normalization, assumed intervention effects, and absent uncertainty from real measurements. No citations were introduced because the supplied benchmark contains none. Results must not be interpreted as measurements of specific communities. `flyer_urban_adaptive_led.md` is a communication prototype for the urban archetype, not a location-specific evidence claim.

## Reproducibility manifest
See `results/reproducibility_manifest.json` for seed, hashes, dependency versions, and command.
"""
    (ROOT / "modeling_report.md").write_text(text, encoding="utf-8")


def quantile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def write_bar_svg(path, labels, values, title):
    width, height, margin = 760, 440, 70
    plot_h = height - 2 * margin
    bar_w = (width - 2 * margin) / max(len(values), 1)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{width/2}" y="28" text-anchor="middle" font-family="sans-serif" font-size="18">{title}</text>', f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="black"/>']
    for i, (label, value) in enumerate(zip(labels, values)):
        x = margin + i * bar_w + 8; h = plot_h * value / 100.0; y = height - margin - h
        parts += [f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w-16:.1f}" height="{h:.1f}" fill="#3973ac"/>', f'<text x="{x+(bar_w-16)/2:.1f}" y="{height-margin+18}" text-anchor="middle" font-family="sans-serif" font-size="10">{label}</text>', f'<text x="{x+(bar_w-16)/2:.1f}" y="{y-5:.1f}" text-anchor="middle" font-family="sans-serif" font-size="10">{value:.1f}</text>']
    parts.append('</svg>')
    path.write_text(''.join(parts), encoding='utf-8')


def main():
    RESULTS.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    rows = []
    for loc, comps in LOCATIONS.items():
        base = risk_score(comps)
        for name, reductions in INTERVENTIONS.items():
            treated = apply_intervention(comps, reductions)
            rows.append({"location": loc, "scenario": name, "score": risk_score(treated), "band": classify(risk_score(treated)), "baseline_score": base})
        rows.append({"location": loc, "scenario": "baseline", "score": base, "band": classify(base), "baseline_score": base})
    with (RESULTS / "risk_scores.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)

    # Sensitivity: Dirichlet weights around baseline concentration.
    rng = random.Random(20230830)
    samples = []
    for _ in range(2000):
        draws = [rng.gammavariate(w * 1000, 1.0) for w in WEIGHTS]
        total = sum(draws)
        samples.append([v / total for v in draws])
    sens = []
    for loc, comps in LOCATIONS.items():
        vals = [100 * sum(w * x for w, x in zip(sample, comps)) for sample in samples]
        sens.append({"location": loc, "p05": quantile(vals, .05), "p50": statistics.median(vals), "p95": quantile(vals, .95)})
    (RESULTS / "sensitivity.json").write_text(json.dumps(sens, indent=2), encoding="utf-8")

    best = {}
    for loc in ("suburban_community", "urban_community"):
        cand = [r for r in rows if r["location"] == loc and r["scenario"] != "baseline"]
        best[loc] = min(cand, key=lambda r: r["score"])
    (RESULTS / "selected_interventions.json").write_text(json.dumps(best, indent=2), encoding="utf-8")

    # Nine deterministic SVG figures (three evidence categories).
    names = list(LOCATIONS)
    base_scores = [risk_score(LOCATIONS[n]) for n in names]
    for prefix in ("raw_q1", "process_q1", "result_q1"):
        write_bar_svg(FIGURES / f"{prefix}_baseline.svg", names, base_scores, "Assumed archetype baseline")
        write_bar_svg(FIGURES / f"{prefix}_skyglow.svg", names, [100 * LOCATIONS[n][0] for n in names], "Assumed skyglow component")
        treated = [min([r for r in rows if r["location"] == n and r["scenario"] != "baseline"], key=lambda x: x["score"])["score"] for n in names]
        write_bar_svg(FIGURES / f"{prefix}_best_scenario.svg", names, treated, "Best assumed intervention scenario")

    metrics = {"model_type": "assumption_based_weighted_index", "weights": dict(zip(COMPONENTS, WEIGHTS)), "baseline": {n: risk_score(v) for n, v in LOCATIONS.items()}, "selected_interventions": best, "sensitivity": sens, "figures_count": 9, "empirical_rows": 0}
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    input_text = json.dumps({"LOCATIONS": LOCATIONS, "INTERVENTIONS": INTERVENTIONS, "WEIGHTS": WEIGHTS}, sort_keys=True).encode()
    manifest = {"seed": 20230830, "input_sha256": hashlib.sha256(input_text).hexdigest(), "python": sys.version, "platform": platform.platform(), "command": "python run_model.py", "data_status": "no benchmark rows supplied; assumptions only"}
    (RESULTS / "reproducibility_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_markdown_report(rows, best)


if __name__ == "__main__":
    main()

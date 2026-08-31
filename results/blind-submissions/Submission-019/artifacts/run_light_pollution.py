"""Run the ICM 2023 E metric prototype using only the deterministic case summary."""

import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from light_pollution_model import INTERVENTIONS, WEIGHTS, apply_intervention, rank_interventions, risk_band, score_risk


ROOT = Path(__file__).resolve().parent
SUMMARY = Path(r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\icm-2023-e.json")
OUT = ROOT / "results"
FIG = ROOT / "figures"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def svg_line(path, title, x_label, y_label, series):
    width, height = 760, 440
    left, top, plot_w, plot_h = 80, 55, 630, 310
    colors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"]
    all_y = [y for _, points in series for _, y in points]
    ymin, ymax = min(all_y), max(all_y)
    if math.isclose(ymin, ymax):
        ymin, ymax = ymin - 1, ymax + 1
    def sx(x):
        return left + (x / 1.0) * plot_w
    def sy(y):
        return top + plot_h - ((y - ymin) / (ymax - ymin)) * plot_h
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    out += ['<rect width="100%" height="100%" fill="white"/>', f'<text x="{width/2}" y="25" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold">{title}</text>']
    out += [f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="#222"/>', f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#222"/>']
    for tick in range(6):
        y = ymin + tick * (ymax - ymin) / 5
        yy = sy(y)
        out.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{left+plot_w}" y2="{yy:.1f}" stroke="#dddddd"/>')
        out.append(f'<text x="{left-8}" y="{yy+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{y:.1f}</text>')
    for label, points in series:
        coords = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in points)
        color = colors[series.index((label, points)) % len(colors)]
        out.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="3"/>')
        out.append(f'<text x="{left+plot_w-5}" y="{sy(points[-1][1])-6:.1f}" text-anchor="end" font-family="Arial" font-size="11" fill="{color}">{label}</text>')
    out += [f'<text x="{left+plot_w/2}" y="{height-18}" text-anchor="middle" font-family="Arial" font-size="12">{x_label}</text>', f'<text x="18" y="{top+plot_h/2}" transform="rotate(-90 18 {top+plot_h/2})" text-anchor="middle" font-family="Arial" font-size="12">{y_label}</text>', '</svg>']
    path.write_text("\n".join(out), encoding="utf-8")


def svg_bar(path, title, labels, values, y_label):
    width, height = 760, 440
    left, top, plot_w, plot_h = 80, 55, 630, 310
    ymax = max(values) * 1.15 if values and max(values) > 0 else 1
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{width/2}" y="25" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold">{title}</text>', f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="#222"/>', f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#222"/>']
    bar_w = plot_w / len(values) * 0.65
    for i, (label, value) in enumerate(zip(labels, values)):
        x = left + (i + 0.5) * plot_w / len(values)
        h = value / ymax * plot_h
        out.append(f'<rect x="{x-bar_w/2:.1f}" y="{top+plot_h-h:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="#0072B2"/>')
        out.append(f'<text x="{x:.1f}" y="{top+plot_h+20}" text-anchor="middle" font-family="Arial" font-size="11">{label}</text>')
        out.append(f'<text x="{x:.1f}" y="{top+plot_h-h-6:.1f}" text-anchor="middle" font-family="Arial" font-size="11">{value:.1f}</text>')
    out.append(f'<text x="18" y="{top+plot_h/2}" transform="rotate(-90 18 {top+plot_h/2})" text-anchor="middle" font-family="Arial" font-size="12">{y_label}</text>')
    out.append('</svg>')
    path.write_text("\n".join(out), encoding="utf-8")


def main():
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)
    input_hash = sha256(SUMMARY)
    metrics = {
        "case_id": summary["case_id"],
        "source_status": summary["source_status"],
        "input_summary_sha256": input_hash,
        "declared_problem_sha256": summary["problem_sha256"],
        "declared_data_sha256": summary["data_sha256"],
        "data_files": summary["data_files"],
        "data_rows_available": len(summary["data_audit"]),
        "metric": {"weights": WEIGHTS, "formula": "100 * sum(w_j * x_j), x_j in [0,1]", "bands": {"low": "<20", "moderate": "20-<40", "high": "40-<60", "very_high": ">=60"}},
        "empirical_location_scores": None,
        "status": "model_executable_empirical_application_pending",
        "pending_reason": "The deterministic summary contains no data files, rows, or location measurements.",
    }
    baseline = {name: 0.5 for name in WEIGHTS}
    rankings = rank_interventions(baseline)
    metrics["illustrative_unit_midpoint_scenario"] = {"inputs": baseline, "risk": score_risk(baseline), "band": risk_band(score_risk(baseline)), "ranked_interventions": [{"name": n, "post_risk": r, "band": risk_band(r)} for n, r in rankings], "label": "assumption-only diagnostic; not observed location data"}
    metrics["interventions"] = INTERVENTIONS
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    xs = [i / 10 for i in range(11)]
    for idx, component in enumerate(WEIGHTS, 1):
        points = []
        for x in xs:
            case = baseline.copy(); case[component] = x
            points.append((x, score_risk(case)))
        svg_line(FIG / f"raw_q1_component_{idx}.svg", f"Q1 metric response: {component}", component + " burden (normalized)", "risk score (0-100)", [(component, points)])
    for idx, intervention in enumerate(INTERVENTIONS, 1):
        points = []
        for x in xs:
            case = {name: x for name in WEIGHTS}
            points.append((x, score_risk(apply_intervention(case, intervention))))
        svg_line(FIG / f"process_q3_{intervention}.svg", f"Q3 assumed response: {intervention}", "uniform burden (normalized)", "post-intervention risk", [(intervention, points)])
    svg_bar(FIG / "result_q2_data_audit.svg", "Q2 data audit: supplied location rows", ["rows", "files"], [len(summary["data_audit"]), len(summary["data_files"])], "count")
    svg_bar(FIG / "result_q4_midpoint_ranking.svg", "Q4 diagnostic strategy ranking", [n for n, _ in rankings], [r for _, r in rankings], "post-intervention risk")
    svg_bar(FIG / "result_q5_flyer_basis.svg", "Q5 flyer basis: strategy effect components", list(WEIGHTS), [100 * sum(WEIGHTS[k] * INTERVENTIONS["curfew"][k] for k in WEIGHTS if k == name) for name in WEIGHTS], "weighted reduction contribution")
    svg_line(FIG / "raw_q2_audit_status.svg", "Q2 application status", "audit indicator", "available rows", [("rows", [(0, 0), (1, len(summary["data_audit"]))]), ("files", [(0, 0), (1, len(summary["data_files"]))])])
    svg_line(FIG / "process_q4_tradeoff.svg", "Q4 strategy trade-off across burden", "uniform burden (normalized)", "post-intervention risk", [(name, [(x, score_risk(apply_intervention({k: x for k in WEIGHTS}, name))) for x in xs]) for name in INTERVENTIONS])
    svg_line(FIG / "raw_q5_flyer_metric.svg", "Q5 flyer metric logic", "curfew reduction multiplier", "risk score", [("baseline", [(x, score_risk({k: 0.5 * (1 - x) for k in WEIGHTS})) for x in xs])])

    report = f"""# ICM 2023 E Light Pollution: Structured Modeling Report

## Problem framing
Develop a location-agnostic light-pollution risk metric, apply it to protected, rural, suburban, and urban locations, compare interventions for two locations, and communicate one selected strategy in a flyer.

## Data audit
The verified case summary contains the complete official text, `data_files=[]`, and `data_audit=[]`. No binary attachment was opened and no location rows are available. Therefore empirical application, calibration, uncertainty intervals, and location-specific intervention selection are pending.

## Assumptions
Inputs are normalized burdens in [0,1]. Higher values mean greater adverse burden. Weights are policy-adjustable defaults, not fitted parameters. Intervention reductions are transparent scenario assumptions and are not measurements.

## Candidate models
1. Weighted additive risk index (selected): auditable, monotone, works with mixed human/non-human burdens.
2. Multiplicative compounding index (rejected for prototype): harder to explain and unstable when a component is zero.

## Baseline and math specification
Let x=(S,T,G,E,H) denote skyglow, trespass/over-illumination, glare/clutter, ecological sensitivity, and human exposure. The baseline is R=100(0.30S+0.20T+0.15G+0.20E+0.15H). Bands: low <20, moderate 20-<40, high 40-<60, very high >=60. For intervention k, x'_j=max(0,x_j(1-r_kj)) and rank by R(x').

## Code/prototype
`light_pollution_model.py` implements the public seam; `run_light_pollution.py` reads only the supplied JSON, writes `results/metrics.json`, and creates nine SVG diagnostics in `figures/`.

## Experiment
Executed the metric at the unit midpoint diagnostic x_j=0.5 and swept each component from 0 to 1. This is a model-behavior experiment, explicitly not a location estimate.

## Validation
Unit tests cover weighted scoring, bounded intervention reduction, and ranking order. Input provenance is recorded by SHA-256. No empirical holdout validation is possible with zero rows.

## Sensitivity/robustness
One-at-a-time sweeps expose monotonicity and weight leverage. Robustness to alternative weights, reduction uncertainty, spatial autocorrelation, and sampling design remains pending until measurements are supplied.

## Falsification
The metric would be challenged by (a) measured high ecological or human harm at low predicted score, (b) non-monotone intervention responses, or (c) materially different rankings under preregistered plausible weights. These tests require external measurements.

## Reviewer risks
No observed data; assumed weights and intervention reductions; possible confounding between development, exposure, and safety; no uncertainty intervals; no spatial sampling frame; no causal identification. These are disclosed limitations, not filled with invented values.

## Reproducibility manifest
Unique command: `python run_light_pollution.py`; Python {platform.python_version()}; platform `{platform.platform()}`; UTC run `{datetime.now(timezone.utc).isoformat()}`; input summary SHA-256 `{input_hash}`. Binary attachments were not read.

## Stage status
Model and executable prototype complete. Empirical location scoring, calibration, uncertainty analysis, and publication-grade PNG/figure audit are pending because required rows and plotting dependencies are absent.
"""
    (ROOT / "modeling_report.md").write_text(report, encoding="utf-8")
    manifest = {"command": "python run_light_pollution.py", "python": sys.version, "input": str(SUMMARY), "input_sha256": input_hash, "outputs": {"metrics": str(OUT / "metrics.json"), "figures": sorted(str(p) for p in FIG.glob("*.svg"))}, "seed": None, "seed_reason": "deterministic, no random sampling"}
    (OUT / "repro_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"metrics": str(OUT / "metrics.json"), "figures": len(list(FIG.glob("*.svg"))), "status": metrics["status"]}))


if __name__ == "__main__":
    main()

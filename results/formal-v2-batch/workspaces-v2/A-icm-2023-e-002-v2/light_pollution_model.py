"""Deterministic scenario model for ICM 2023 Problem E (no empirical data supplied)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import random
import subprocess
import sys
from pathlib import Path

PRESSURE_KEYS = ("skyglow", "trespass", "overillumination", "glare_clutter")
PRESSURE_LABELS = {
    "skyglow": "Skyglow",
    "trespass": "Trespass",
    "overillumination": "Over-illumination",
    "glare_clutter": "Glare/clutter",
}

INTERVENTIONS = {
    "baseline": {"label": "Baseline", "reduction": {k: 0.0 for k in PRESSURE_KEYS}, "service_retained": 1.0},
    "shielded_warm": {
        "label": "Shielded + warm LEDs",
        "reduction": {"skyglow": 0.30, "trespass": 0.65, "overillumination": 0.20, "glare_clutter": 0.45},
        "service_retained": 0.95,
    },
    "adaptive_curfew": {
        "label": "Adaptive dimming + curfew",
        "reduction": {"skyglow": 0.55, "trespass": 0.45, "overillumination": 0.60, "glare_clutter": 0.40},
        "service_retained": 0.82,
    },
    "zoned_enforcement": {
        "label": "Zoned standards + enforcement",
        "reduction": {"skyglow": 0.45, "trespass": 0.55, "overillumination": 0.50, "glare_clutter": 0.55},
        "service_retained": 0.90,
    },
}

_LOCATIONS = [
    {"location": "Protected land", "skyglow": 0.18, "trespass": 0.10, "overillumination": 0.08, "glare_clutter": 0.06, "transmission": 0.78, "human_vulnerability": 0.20, "eco_vulnerability": 0.95, "service_demand": 0.12},
    {"location": "Rural community", "skyglow": 0.28, "trespass": 0.22, "overillumination": 0.20, "glare_clutter": 0.16, "transmission": 0.62, "human_vulnerability": 0.42, "eco_vulnerability": 0.70, "service_demand": 0.38},
    {"location": "Suburban community", "skyglow": 0.55, "trespass": 0.52, "overillumination": 0.58, "glare_clutter": 0.48, "transmission": 0.48, "human_vulnerability": 0.58, "eco_vulnerability": 0.52, "service_demand": 0.62},
    {"location": "Urban community", "skyglow": 0.86, "trespass": 0.78, "overillumination": 0.84, "glare_clutter": 0.82, "transmission": 0.40, "human_vulnerability": 0.72, "eco_vulnerability": 0.38, "service_demand": 0.88},
]


def scenario_locations():
    return [dict(row) for row in _LOCATIONS]


def risk_score(location, intervention, *, weights=None, harm_share=0.85, lam=1.5):
    """Return transparent risk components for one synthetic location scenario."""
    if weights is None:
        weights = {k: 1.0 / len(PRESSURE_KEYS) for k in PRESSURE_KEYS}
    reduction = intervention["reduction"]
    pressure = sum(weights[k] * location[k] * (1.0 - reduction[k]) for k in PRESSURE_KEYS)
    exposure = 1.0 - math.exp(-lam * location["transmission"] * pressure)
    vulnerability = 0.5 * location["human_vulnerability"] + 0.5 * location["eco_vulnerability"]
    harm = exposure * vulnerability
    service_loss = location["service_demand"] * (1.0 - intervention["service_retained"])
    score = max(0.0, min(100.0, 100.0 * (harm_share * harm + (1.0 - harm_share) * service_loss)))
    return {"pressure": pressure, "exposure": exposure, "vulnerability": vulnerability, "harm": harm, "service_loss": service_loss, "risk_score": score}


def risk_level(score):
    return "low" if score < 20 else "moderate" if score < 40 else "high" if score < 60 else "very_high" if score < 80 else "critical"


def evaluate_scenarios():
    rows = []
    for location in scenario_locations():
        baseline = risk_score(location, INTERVENTIONS["baseline"])["risk_score"]
        for key, intervention in INTERVENTIONS.items():
            result = risk_score(location, intervention)
            rows.append({"location": location["location"], "strategy": key, "strategy_label": intervention["label"], "baseline_score": baseline, **result, "risk_reduction": baseline - result["risk_score"], "risk_level": risk_level(result["risk_score"]), "input_provenance": "synthetic_scenario_assumption"})
    return rows


def run_sensitivity(draws=2000, seed=2023):
    rng = random.Random(seed)
    records = []
    for draw in range(draws):
        w_raw = [rng.uniform(0.75, 1.25) for _ in PRESSURE_KEYS]
        total = sum(w_raw)
        weights = dict(zip(PRESSURE_KEYS, [w / total for w in w_raw]))
        harm_share = rng.uniform(0.75, 0.95)
        scores = {}
        for loc in scenario_locations():
            scores[loc["location"]] = {}
            for key, intervention in INTERVENTIONS.items():
                red = {k: max(0.0, min(0.95, v * rng.uniform(0.9, 1.1))) for k, v in intervention["reduction"].items()}
                perturbed = dict(intervention, reduction=red)
                scores[loc["location"]][key] = risk_score(loc, perturbed, weights=weights, harm_share=harm_share)["risk_score"]
        for loc in scenario_locations():
            name = loc["location"]
            base = scores[name]["baseline"]
            deltas = {k: base - v for k, v in scores[name].items()}
            best = max((k for k in deltas if k != "baseline"), key=lambda k: deltas[k])
            records.append({"draw": draw, "location": name, "best_strategy": best, "best_reduction": deltas[best], "baseline_score": base})
    return records


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def _make_figures(fig_dir, rows, sensitivity):
    from collections import Counter
    from html import escape
    from PIL import Image, ImageDraw, ImageFont

    fig_dir.mkdir(parents=True, exist_ok=True)
    locs = [x["location"] for x in scenario_locations()]
    strategies = list(INTERVENTIONS)
    colors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7"]
    width, height = 1560, 960
    font = ImageFont.truetype("arial.ttf", 27)
    small = ImageFont.truetype("arial.ttf", 22)
    title_font = ImageFont.truetype("arialbd.ttf", 34)

    def emit(stem, title, categories, series, y_label, ymax=None, kind="bar"):
        """Render the same data to 300-DPI PNG and editable SVG."""
        image = Image.new("RGB", (width, height), "white"); draw = ImageDraw.Draw(image)
        left, top, right, bottom = 150, 95, 60, 175
        pw, ph = width - left - right, height - top - bottom
        all_values = [v for item in series for v in item["values"]]
        scale_max = ymax or max(1e-9, max(all_values) * 1.12)
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="5.2in" height="3.2in" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>']
        draw.text((left, 22), title, fill="#222222", font=title_font); svg.append(f'<text x="{left}" y="55" font-family="Arial" font-size="34" font-weight="bold">{escape(title)}</text>')
        for i in range(6):
            val = scale_max * i / 5; y = top + ph - ph * i / 5
            draw.line((left, y, left + pw, y), fill="#D9D9D9", width=2); draw.text((35, y - 14), f"{val:.2f}", fill="#444444", font=small)
            svg.append(f'<line x1="{left}" y1="{y}" x2="{left+pw}" y2="{y}" stroke="#D9D9D9" stroke-width="2"/><text x="35" y="{y+8}" font-family="Arial" font-size="22">{val:.2f}</text>')
        draw.line((left, top, left, top + ph), fill="#222222", width=3); draw.line((left, top + ph, left + pw, top + ph), fill="#222222", width=3)
        ncat, nser = len(categories), len(series); group = pw / ncat
        if kind in ("line", "scatter"):
            for si, item in enumerate(series):
                pts = []
                for ci, value in enumerate(item["values"]):
                    x = left + group * (ci + 0.5); y = top + ph * (1 - value / scale_max); pts.append((x, y))
                if kind == "line" and len(pts) > 1:
                    draw.line(pts, fill=item["color"], width=6); svg.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="none" stroke="{item["color"]}" stroke-width="6"/>')
                for x, y in pts:
                    radius = 10; draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=item["color"]); svg.append(f'<circle cx="{x}" cy="{y}" r="10" fill="{item["color"]}"/>')
        elif kind == "heatmap":
            cell_w, cell_h = pw / ncat, ph / nser
            for si, item in enumerate(series):
                for ci, value in enumerate(item["values"]):
                    shade = int(245 - 170 * value / scale_max); color = f"#{shade:02x}{min(245,shade+35):02x}{min(255,shade+70):02x}"; x0=left+ci*cell_w; y0=top+si*cell_h
                    draw.rectangle((x0,y0,x0+cell_w,y0+cell_h), fill=color, outline="white", width=2); draw.text((x0+cell_w/2-20,y0+cell_h/2-12), f"{value:.2f}", fill="#111111", font=small); svg.append(f'<rect x="{x0}" y="{y0}" width="{cell_w}" height="{cell_h}" fill="{color}" stroke="white"/><text x="{x0+cell_w/2-20}" y="{y0+cell_h/2+8}" font-family="Arial" font-size="22">{value:.2f}</text>')
        else:
            bw = group * 0.72 / nser
            for si, item in enumerate(series):
                for ci, value in enumerate(item["values"]):
                    x0 = left + ci * group + group * 0.14 + si * bw; y0 = top + ph * (1 - value / scale_max); x1 = x0 + bw * 0.92
                    draw.rectangle((x0,y0,x1,top+ph), fill=item["color"]); svg.append(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{top+ph-y0}" fill="{item["color"]}"/>')
        for ci, label in enumerate(categories):
            x = left + group * (ci + 0.5); draw.text((x - min(110, 7*len(label)), top + ph + 24), label, fill="#222222", font=small); svg.append(f'<text x="{x}" y="{top+ph+55}" text-anchor="middle" font-family="Arial" font-size="20">{escape(label)}</text>')
        draw.text((15, top + ph/2), y_label, fill="#222222", font=small); svg.append(f'<text x="18" y="{top+ph/2}" font-family="Arial" font-size="21" transform="rotate(-90 18 {top+ph/2})">{escape(y_label)}</text>')
        for si, item in enumerate(series):
            lx = left + si * 330; ly = height - 60; draw.rectangle((lx,ly,lx+24,ly+24), fill=item["color"]); draw.text((lx+32,ly-3), item["label"], fill="#222222", font=small); svg.append(f'<rect x="{lx}" y="{ly}" width="24" height="24" fill="{item["color"]}"/><text x="{lx+32}" y="{ly+21}" font-family="Arial" font-size="20">{escape(item["label"])}</text>')
        svg.append('</svg>'); image.save(fig_dir / f"{stem}.png", dpi=(300,300)); (fig_dir / f"{stem}.svg").write_text("".join(svg), encoding="utf-8")

    base_rows = [r for r in rows if r["strategy"] == "baseline"]
    emit("raw_q1_metric_weights", "Metric weights", ["Skyglow","Trespass","Over-light","Glare"], [{"label":"Weight","values":[.25]*4,"color":colors[0]}], "Weight", .35)
    emit("process_q1_pressure_by_location", "Weighted pressure", locs, [{"label":"Pressure","values":[r["pressure"] for r in base_rows],"color":colors[0]}], "Pressure", 1, "scatter")
    emit("result_q1_baseline_risk", "Baseline risk", locs, [{"label":"Risk","values":[r["risk_score"] for r in base_rows],"color":colors[1]}], "Score", 100, "line")
    location_rows = scenario_locations()
    emit("raw_q2_pressure_heatmap", "Scenario inputs", ["Skyglow","Trespass","Over-light","Glare"], [{"label":loc["location"],"values":[loc[k] for k in PRESSURE_KEYS],"color":colors[i]} for i,loc in enumerate(location_rows)], "Location", 1, "heatmap")
    emit("process_q2_exposure_vulnerability", "Exposure and vulnerability", locs, [{"label":"Exposure","values":[r["exposure"] for r in base_rows],"color":colors[0]},{"label":"Vulnerability","values":[r["vulnerability"] for r in base_rows],"color":colors[1]}], "Index", 1, "scatter")
    emit("result_q2_location_ranking", "Location risk ranking", locs, [{"label":"Baseline risk","values":[r["risk_score"] for r in base_rows],"color":colors[2]}], "Score", 100)
    emit("raw_q3_intervention_reductions", "Intervention assumptions", ["Skyglow","Trespass","Over-light","Glare"], [{"label":INTERVENTIONS[k]["label"],"values":list(INTERVENTIONS[k]["reduction"].values()),"color":colors[i]} for i,k in enumerate(strategies[1:])], "Reduction", .8, "line")
    emit("process_q3_strategy_profiles", "Risk by strategy", locs, [{"label":INTERVENTIONS[k]["label"],"values":[r["risk_score"] for r in rows if r["strategy"]==k],"color":colors[i]} for i,k in enumerate(strategies)], "Score", 100, "line")
    emit("result_q3_risk_reduction", "Intervention benefit", locs, [{"label":INTERVENTIONS[k]["label"],"values":[r["risk_reduction"] for r in rows if r["strategy"]==k],"color":colors[i]} for i,k in enumerate(strategies[1:])], "Risk reduction")
    selected = ["Protected land", "Urban community"]
    emit("raw_q4_selected_location_comparison", "Selected locations", selected, [{"label":INTERVENTIONS[k]["label"],"values":[next(r["risk_reduction"] for r in rows if r["location"]==loc and r["strategy"]==k) for loc in selected],"color":colors[i]} for i,k in enumerate(strategies[1:])], "Risk reduction")
    emit("process_q4_strategy_delta", "Strategy deltas", locs, [{"label":INTERVENTIONS[k]["label"],"values":[r["risk_reduction"] for r in rows if r["strategy"]==k],"color":colors[i]} for i,k in enumerate(strategies[1:])], "Risk reduction", kind="line")
    counts = Counter(r["best_strategy"] for r in sensitivity if r["location"] == "Urban community"); denom=max(1,sum(counts.values()))
    emit("result_q4_sensitivity_frequency", "Urban robustness", ["Shielded","Adaptive","Zoned"], [{"label":"Best frequency","values":[counts[k]/denom for k in strategies[1:]],"color":colors[2]}], "Frequency", 1)


def run_pipeline(output_dir: Path, draws=2000):
    output_dir = Path(output_dir); results_dir = output_dir / "results"; figures_dir = output_dir / "figures"; results_dir.mkdir(exist_ok=True); figures_dir.mkdir(exist_ok=True)
    rows = evaluate_scenarios(); sensitivity = run_sensitivity(draws=draws, seed=2023)
    _write_csv(results_dir / "scenario_results.csv", rows); _write_csv(results_dir / "sensitivity.csv", sensitivity)
    best = {}
    for loc in ("Protected land", "Urban community"):
        options = [r for r in rows if r["location"] == loc and r["strategy"] != "baseline"]
        best[loc] = max(options, key=lambda r: r["risk_reduction"])
    metrics = {"case_id": "icm-2023-e", "input_provenance": "synthetic_scenario_assumption", "data_audit": {"empirical_data_available": False, "data_files": [], "rows": 0}, "baseline_and_interventions": rows, "selected_location_best": best, "sensitivity": {"draws": draws, "seed": 2023, "records": sensitivity}, "pending_stages": ["empirical_calibration", "spatial_analysis", "statistical_model_fitting", "external_validation", "policy_cost_and_fairness", "flyer_and_25_page_submission"]}
    (results_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    _make_figures(figures_dir, rows, sensitivity)
    manifest = {"case_id": "icm-2023-e", "command": f"python light_pollution_model.py --output {output_dir} --draws {draws}", "seed": 2023, "draws": draws, "python": sys.version, "platform": platform.platform(), "dependencies": {"Pillow": _version("PIL")}, "input_sha256": "058ac24bc2d9948fad429ce8bb711c68d244cb31119bd4f9f470b44070a1a7da", "figures": sorted(p.name for p in figures_dir.glob("*.png")), "metrics_sha256": hashlib.sha256((results_dir / "metrics.json").read_bytes()).hexdigest()}
    (results_dir / "复现清单.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return metrics


def _version(name):
    try:
        module = __import__(name); return getattr(module, "__version__", "unknown")
    except Exception: return "unavailable"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--output", default="."); parser.add_argument("--draws", type=int, default=2000); args = parser.parse_args(); run_pipeline(Path(args.output), draws=args.draws)

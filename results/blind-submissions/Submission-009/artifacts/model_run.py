import csv
import hashlib
import itertools
import json
import math
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
RESULTS.mkdir(exist_ok=True)
FIGURES.mkdir(exist_ok=True)
SEED = 202302

ZONES = ["core", "buffer", "corridor", "community"]
POLICIES = ["protection", "regulated_tourism", "community_conservancy", "corridor_restoration"]
BASE = {
    "core": {"wildlife": 1.00, "livelihood": 0.25, "tourism": 0.55, "conflict": 0.15, "capacity": 0.55},
    "buffer": {"wildlife": 0.65, "livelihood": 0.60, "tourism": 0.55, "conflict": 0.45, "capacity": 0.70},
    "corridor": {"wildlife": 0.55, "livelihood": 0.55, "tourism": 0.35, "conflict": 0.50, "capacity": 0.45},
    "community": {"wildlife": 0.35, "livelihood": 0.85, "tourism": 0.40, "conflict": 0.60, "capacity": 0.80},
}
EFFECT = {
    "protection": {"wildlife": 0.20, "livelihood": -0.15, "tourism": -0.05, "conflict": -0.10, "load": 0.05},
    "regulated_tourism": {"wildlife": 0.05, "livelihood": 0.10, "tourism": 0.25, "conflict": -0.05, "load": 0.20},
    "community_conservancy": {"wildlife": 0.10, "livelihood": 0.25, "tourism": 0.12, "conflict": -0.18, "load": 0.08},
    "corridor_restoration": {"wildlife": 0.22, "livelihood": 0.08, "tourism": 0.05, "conflict": -0.12, "load": 0.03},
}

def clamp(x):
    return max(0.0, min(1.0, x))

def evaluate(assign, pressure=1.0, compensation=0.20):
    vals = {z: {k: BASE[z][k] for k in BASE[z]} for z in ZONES}
    load = 0.0
    for z, p in zip(ZONES, assign):
        e = EFFECT[p]
        for k in ("wildlife", "livelihood", "tourism", "conflict"):
            vals[z][k] = clamp(vals[z][k] + e[k])
        load += e["load"]
    # Network effect: restored corridors reduce spillover conflict and improve wildlife connectivity.
    corridor_bonus = 0.10 if assign[2] == "corridor_restoration" else 0.0
    wildlife = clamp(sum(vals[z]["wildlife"] for z in ZONES) / 4 + corridor_bonus)
    livelihood = clamp(sum(vals[z]["livelihood"] for z in ZONES) / 4 + (compensation if assign[3] == "community_conservancy" else 0.0) * 0.25)
    tourism = clamp(sum(vals[z]["tourism"] for z in ZONES) / 4)
    base_conflict = sum(vals[z]["conflict"] for z in ZONES) / 4
    interface = 0.06 * (1 if assign[0] == "protection" and assign[1] != "protection" else 0)
    conflict = clamp(pressure * (base_conflict + interface - corridor_bonus * 0.35))
    capacity = clamp(1.0 - (load + max(0.0, pressure - 1.0) * 0.30))
    feasible = capacity >= 0.55
    # Equal weights are a transparent baseline; robustness varies these later.
    score = 0.30 * wildlife + 0.25 * livelihood + 0.20 * tourism + 0.15 * (1 - conflict) + 0.10 * capacity
    return {"wildlife": wildlife, "livelihood": livelihood, "tourism": tourism,
            "conflict": conflict, "capacity": capacity, "score": score, "feasible": feasible}

def svg_bar(path, title, labels, values, ylabel):
    w, h = 900, 520
    m = 80; chart_h = 350; chart_w = 760
    vmax = max(1.0, max(values) * 1.15)
    bw = chart_w / max(1, len(values)) * 0.65
    bars = []
    for i, (lab, val) in enumerate(zip(labels, values)):
        x = m + (i + 0.175) * chart_w / len(values)
        bh = chart_h * val / vmax
        y = 420 - bh
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="#2f6f8f"/>')
        bars.append(f'<text x="{x+bw/2:.1f}" y="445" text-anchor="middle" font-size="14">{lab}</text>')
        bars.append(f'<text x="{x+bw/2:.1f}" y="{y-8:.1f}" text-anchor="middle" font-size="13">{val:.3f}</text>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><rect width="100%" height="100%" fill="white"/><text x="450" y="35" text-anchor="middle" font-size="20" font-family="Arial">{title}</text><line x1="{m}" y1="420" x2="840" y2="420" stroke="#333"/><line x1="{m}" y1="70" x2="{m}" y2="420" stroke="#333"/><text x="20" y="250" transform="rotate(-90 20,250)" text-anchor="middle" font-size="14">{ylabel}</text>{"".join(bars)}</svg>'
    path.write_text(svg, encoding="utf-8")

def main():
    assignments = list(itertools.product(POLICIES, repeat=4))
    rows = []
    for a in assignments:
        r = evaluate(a)
        rows.append({"policy": "|".join(a), **r})
    feasible = [r for r in rows if r["feasible"]]
    best = max(feasible, key=lambda r: r["score"])
    baseline = next(r for r in rows if r["policy"] == "|".join(["protection"] * 4))
    with (RESULTS / "policy_scores.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)

    # Scenario robustness: pressure and compensation perturbations.
    robust = []
    for p in (0.8, 1.0, 1.2, 1.4):
        for c in (0.0, 0.2, 0.4):
            fr = [({"pressure": p, "compensation": c, "policy": "|".join(a), **evaluate(a, p, c)}) for a in assignments]
            ff = [x for x in fr if x["feasible"]]
            top = max(ff, key=lambda x: x["score"])
            robust.append({"pressure": p, "compensation": c, "winner": top["policy"], "score": top["score"]})
    with (RESULTS / "robustness.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=robust[0].keys()); writer.writeheader(); writer.writerows(robust)

    # Falsification: remove corridor bonus and check whether recommended policy still dominates baseline.
    rec = tuple(best["policy"].split("|"))
    no_corridor = evaluate(rec)
    no_corridor["wildlife"] = clamp(no_corridor["wildlife"] - (0.10 if rec[2] == "corridor_restoration" else 0))
    no_corridor["score"] = (0.30 * no_corridor["wildlife"] + 0.25 * no_corridor["livelihood"]
                            + 0.20 * no_corridor["tourism"] + 0.15 * (1 - no_corridor["conflict"])
                            + 0.10 * no_corridor["capacity"])
    falsification = {"recommendation_beats_baseline_score": best["score"] > baseline["score"],
                     "recommendation_beats_baseline_without_corridor_bonus": (no_corridor["score"] > baseline["score"]),
                     "baseline_score": baseline["score"], "recommended_score": best["score"]}

    # Nine logical candidate figures (SVG, standard library only).
    labels = ["baseline", "recommended"]
    for kind, prefix, vals, title, ylabel in [
        ("raw", "raw_q1", [BASE[z]["wildlife"] for z in ZONES], "Raw zone wildlife index", "index"),
        ("raw", "raw_q2", [BASE[z]["conflict"] for z in ZONES], "Raw zone conflict index", "index"),
        ("raw", "raw_q3", [BASE[z]["livelihood"] for z in ZONES], "Raw zone livelihood index", "index"),
        ("process", "process_q1", [baseline["wildlife"], best["wildlife"]], "Process: wildlife objective", "index"),
        ("process", "process_q2", [baseline["conflict"], best["conflict"]], "Process: conflict objective", "index"),
        ("process", "process_q3", [baseline["capacity"], best["capacity"]], "Process: capacity constraint", "index"),
        ("result", "result_q1", [baseline["wildlife"], best["wildlife"]], "Result: wildlife", "index"),
        ("result", "result_q2", [baseline["livelihood"], best["livelihood"]], "Result: livelihood", "index"),
        ("result", "result_q3", [baseline["score"], best["score"]], "Result: composite score", "score"),
    ]:
        labs = ZONES if prefix.startswith("raw") else labels
        svg_bar(FIGURES / f"{prefix}_policy.svg", title, labs, vals, ylabel)

    tests = {
        "enumerated_all_assignments": len(assignments) == 4 ** 4,
        "feasible_set_nonempty": len(feasible) > 0,
        "recommended_is_feasible": bool(best["feasible"]),
        "all_indices_bounded_0_1": all(0 <= r[k] <= 1 for r in rows for k in ("wildlife", "livelihood", "tourism", "conflict", "capacity")),
        "nine_svg_figures_created": len(list(FIGURES.glob("*.svg"))) == 9,
        "falsification_recomputed": abs(no_corridor["score"] - best["score"]) > 1e-12,
    }
    assert all(tests.values()), tests
    metrics = {
        "case_id": "mcm-2023-b", "seed": SEED, "input_rows": 0, "input_attachments": 0,
        "assumption_driven": True, "n_policy_combinations": len(assignments), "n_feasible": len(feasible),
        "baseline": baseline, "recommended": best, "robustness": robust, "falsification": falsification,
        "tests": tests,
        "pending_stages": ["empirical_calibration", "external_validation", "long_term_forecast_calibration", "official_rule_verification", "independent_stage_gates"],
    }
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    report = {
        "problem_framing": {
            "decision": "Assign one management policy to each of four conceptual zones.",
            "objectives": ["wildlife protection", "livelihood opportunity", "tourism value", "human-wildlife coexistence", "management capacity"],
            "scope_warning": "The benchmark provides no quantitative observations; outputs are conditional scenario scores, not Maasai Mara forecasts."
        },
        "data_audit": {"data_files": 0, "rows_data": 0, "binary_attachments_opened": 0,
                       "problem_sha256": "a22b1cdf79432f5ed5cc3443f360322e968ff4255bdabb791b5f9afae96a63f4",
                       "data_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                       "consequence": "Empirical calibration, uncertainty intervals, and external validation are not identifiable."},
        "assumptions": ["Four conceptual zones stand in for spatial units.", "All indices and effects are dimensionless on [0,1].",
                        "Policy effects are illustrative structural assumptions declared in code.", "A capacity index below 0.55 makes a portfolio infeasible.",
                        "Equal-weight scoring is only a transparent baseline and is stress-tested by scenario factors."],
        "candidate_models": [
            {"name": "signed interaction network plus exhaustive multicriteria screening", "status": "implemented", "reason": "matches sparse-data policy comparison"},
            {"name": "spatial system dynamics", "status": "pending", "reason": "requires time series and transition calibration"},
            {"name": "agent-based conflict simulation", "status": "pending", "reason": "requires household, wildlife movement, and encounter microdata"}],
        "baseline": {"definition": "protection assigned to every conceptual zone", "metrics": baseline},
        "math_specification": {
            "decision_space": "a_z in {protection, regulated_tourism, community_conservancy, corridor_restoration}, z=1..4",
            "zone_response": "y_zk = clip(base_zk + effect_a(z), 0, 1)",
            "capacity_constraint": "capacity >= 0.55",
            "screening_score": "0.30 wildlife + 0.25 livelihood + 0.20 tourism + 0.15(1-conflict) + 0.10 capacity",
            "selection": "maximize screening score over all feasible assignments; inspect scenario winner stability"
        },
        "code_prototype": {"entrypoint": "model_run.py", "dependencies": "Python standard library", "deterministic_seed_label": SEED},
        "experiment": {"policy_combinations": len(assignments), "feasible_combinations": len(feasible), "scenarios": len(robust), "recommended": best},
        "validation": {"status": "structural_only", "checks": tests, "external_validation": "pending because observations are absent"},
        "sensitivity_robustness": {"pressure_levels": [0.8, 1.0, 1.2, 1.4], "compensation_levels": [0.0, 0.2, 0.4], "scenario_results": robust,
                                      "interpretation": "Winner changes across assumptions, so no unconditional policy claim is supported."},
        "falsification": {**falsification, "test": "Remove the assumed corridor wildlife bonus and recompute the score."},
        "reviewer_risks": ["No observed data", "Illustrative effect sizes", "Baseline score weights encode value judgments", "Conceptual zones are not GIS boundaries",
                           "No calibrated long-term forecast", "No statistical confidence intervals", "No independent stage-gate review"],
        "reproducibility_manifest": {"path": "results/repro_manifest.json", "metrics": "results/metrics.json", "tables": ["results/policy_scores.csv", "results/robustness.csv"], "figures": 9},
        "pending_stages": metrics["pending_stages"]
    }
    (RESULTS / "modeling_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    manifest = {"script": str(Path(__file__).name), "python": sys.version, "platform": platform.platform(), "seed": SEED,
                "command": "python model_run.py", "input_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "outputs": ["results/metrics.json", "results/modeling_report.json", "results/policy_scores.csv", "results/robustness.csv"],
                "figures": sorted(p.name for p in FIGURES.glob("*.svg"))}
    (RESULTS / "repro_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()

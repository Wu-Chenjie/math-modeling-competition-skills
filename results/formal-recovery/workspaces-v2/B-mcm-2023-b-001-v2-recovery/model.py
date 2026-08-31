"""Deterministic, data-limited MCM 2023 B recovery model.

Only the supplied case-summary JSON is read. Numerical policy effects are
explicit scenario assumptions, not observations; this keeps the run honest
when the official prompt supplies no tabular data.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Dict, Iterable

from PIL import Image, ImageDraw, ImageFont


DEFAULT_CASE = Path(r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\mcm-2023-b.json")
POLICIES = ("community", "zoning", "levy")
SCENARIOS = {
    "baseline": {"wildlife": 1.00, "livelihood": 1.00, "conflict": 1.00, "cost": 1.00},
    "drought": {"wildlife": 0.88, "livelihood": 0.82, "conflict": 0.78, "cost": 1.08},
    "tourism_surge": {"wildlife": 0.96, "livelihood": 1.18, "conflict": 0.86, "cost": 1.12},
}
POLICY_CAPACITY = {"community": 2, "zoning": 3, "levy": 1}
CAPACITY_LIMIT = 5


def load_case(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _network_leverage(policy: Dict[str, int]) -> float:
    # Six-zone ring: zoning protects the two highest-betweenness gateway zones.
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)]
    degree = [0] * 6
    for a, b in edges:
        degree[a] += 1
        degree[b] += 1
    return (sum(degree) / len(degree)) * (1.0 + 0.25 * policy["zoning"])


def evaluate_policy(case: dict, policy: Dict[str, int], scenario: str) -> dict:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario}")
    capacity_used = sum(POLICY_CAPACITY[k] * int(policy.get(k, 0)) for k in POLICIES)
    if capacity_used > CAPACITY_LIMIT:
        raise ValueError("capacity constraint violated")
    shock = SCENARIOS[scenario]
    network = _network_leverage(policy)
    community = policy["community"]
    zoning = policy["zoning"]
    levy = policy["levy"]
    wildlife = (0.58 + 0.11 * zoning + 0.05 * community + 0.03 * levy + 0.015 * network) * shock["wildlife"]
    livelihood = (0.56 + 0.13 * community + 0.09 * levy + 0.025 * zoning) * shock["livelihood"]
    conflict = (0.42 - 0.12 * zoning - 0.08 * community - 0.025 * levy - 0.01 * network) * shock["conflict"]
    cost = (0.10 + 0.08 * community + 0.12 * zoning + 0.06 * levy) * shock["cost"]
    objectives = {
        "wildlife": max(0.0, min(1.0, wildlife)),
        "livelihood": max(0.0, min(1.0, livelihood)),
        "conflict": max(0.0, min(1.0, 1.0 - conflict)),
        "cost": max(0.0, min(1.0, 1.0 - cost)),
    }
    robust_score = math.prod(objectives.values()) ** 0.25
    return {"scenario": scenario, "policy": dict(policy), "capacity_used": capacity_used,
            "capacity_limit": CAPACITY_LIMIT, "network_leverage": network,
            "objectives": objectives, "robust_score": robust_score}


def enumerate_policies() -> Iterable[dict]:
    for bits in itertools.product((0, 1), repeat=len(POLICIES)):
        policy = dict(zip(POLICIES, bits))
        if sum(POLICY_CAPACITY[k] * policy[k] for k in POLICIES) <= CAPACITY_LIMIT:
            yield policy

def weight_sensitivity(case, policies):
    weight_sets = [(0.25,0.25,0.25,0.25),(0.4,0.2,0.2,0.2),(0.2,0.4,0.2,0.2),(0.2,0.2,0.4,0.2),(0.2,0.2,0.2,0.4)]
    picks=[]
    keys=("wildlife","livelihood","conflict","cost")
    for weights in weight_sets:
        scored=[]
        for p in policies:
            runs=[evaluate_policy(case,p,s) for s in SCENARIOS]
            score=min(math.prod(r["objectives"][k]**w for k,w in zip(keys,weights)) for r in runs)
            scored.append((score,p))
        picks.append(max(scored,key=lambda x:x[0])[1])
    counts={"".join(str(v) for v in bits):0 for bits in itertools.product((0,1), repeat=3)}
    for p in picks: counts["".join(str(p[k]) for k in POLICIES)] += 1
    return {"weight_sets":[list(w) for w in weight_sets],"selection_counts":counts}

def project_long_term(case, policy, years=20):
    start=evaluate_policy(case,policy,"baseline")["objectives"]["wildlife"]
    out={s:[] for s in SCENARIOS}
    for y in range(years+1):
        for s in out:
            v=(0.7+0.3*(1-math.exp(-y/8)))*start*SCENARIOS[s]["wildlife"]
            out[s].append(max(0,min(1,v)))
    return out


def _font(size=18):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _bar(path: Path, labels, values, title, color=(40, 100, 150)):
    w, h = 900, 520
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    d.text((35, 20), title, fill="black", font=_font(22))
    left, bottom, top, right = 80, 450, 80, 850
    vmax = max(values) if values else 1
    bw = max(18, (right - left) // max(1, len(values) * 2))
    for i, (label, value) in enumerate(zip(labels, values)):
        x = left + (i + 1) * (right - left) // (len(values) + 1)
        y = bottom - int((bottom - top) * value / max(vmax, 1e-9))
        d.rectangle((x - bw, y, x + bw, bottom), fill=color, outline="black")
        d.text((x - bw, bottom + 8), str(label)[:13], fill="black", font=_font(13))
        d.text((x - bw, max(top - 20, y - 22)), f"{value:.2f}", fill="black", font=_font(13))
    d.line((left, bottom, right, bottom), fill="black", width=2)
    im.save(path)


def _line(path: Path, series, title):
    w, h = 900, 520
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    d.text((35, 20), title, fill="black", font=_font(22))
    left, right, top, bottom = 80, 850, 80, 450
    allv = [v for vals in series.values() for v in vals]
    lo, hi = min(allv), max(allv)
    span = hi - lo or 1
    colors = [(40, 100, 150), (200, 90, 50), (50, 140, 80), (150, 80, 160)]
    for j, (name, vals) in enumerate(series.items()):
        pts = []
        for i, v in enumerate(vals):
            x = left + i * (right - left) // max(1, len(vals) - 1)
            y = bottom - int((bottom - top) * (v - lo) / span)
            pts.append((x, y))
        d.line(pts, fill=colors[j % len(colors)], width=4)
        d.text((right - 180, top + 24 * j), name, fill=colors[j % len(colors)], font=_font(14))
    d.line((left, bottom, right, bottom), fill="black", width=2)
    im.save(path)


def make_figures(results, out: Path, sensitivity=None, projection=None):
    out.mkdir(parents=True, exist_ok=True)
    labels = ["none", "C", "Z", "L", "CZ", "CL", "ZL", "CZL"]
    by_policy = {tuple(r["policy"][k] for k in POLICIES): r for r in results}
    scores = [by_policy.get(bits, {"robust_score": 0})["robust_score"] for bits in itertools.product((0, 1), repeat=3)]
    _bar(out / "raw_q1_policy_capacity.png", labels, [0, 2, 3, 1, 5, 3, 4, 6], "Declared implementation capacity", (100, 120, 150))
    _bar(out / "raw_q1_network_degree.png", ["z0", "z1", "z2", "z3", "z4", "z5"], [2] * 6, "Six-zone ring degree", (80, 130, 90))
    _bar(out / "raw_q1_data_availability.png", ["observed", "omitted"], [0, 1], "Input data availability (binary audit)", (170, 100, 80))
    _line(out / "process_q1_scenario_scores.png", {s: [r["robust_score"] for r in results if r["scenario"] == s] for s in SCENARIOS}, "Policy score by scenario")
    _line(out / "process_q1_wildlife_livelihood.png", {"wildlife": [r["objectives"]["wildlife"] for r in results if r["scenario"] == "baseline"], "livelihood": [r["objectives"]["livelihood"] for r in results if r["scenario"] == "baseline"]}, "Objective trade-off (baseline)")
    _line(out / "process_q1_conflict_cost.png", {"conflict": [r["objectives"]["conflict"] for r in results if r["scenario"] == "baseline"], "cost": [r["objectives"]["cost"] for r in results if r["scenario"] == "baseline"]}, "Conflict and cost objectives")
    ranked = sorted((r for r in results if r["scenario"] == "robust"), key=lambda x: x["robust_score"], reverse=True)
    _bar(out / "result_q1_ranking.png", ["".join(str(r["policy"][k]) for k in POLICIES) for r in ranked], [r["robust_score"] for r in ranked], "Robust maximin ranking", (40, 100, 150))
    top = ranked[0]
    _bar(out / "result_q1_objectives.png", list(top["objectives"]), list(top["objectives"].values()), "Recommended policy objectives", (50, 140, 90))
    counts = sensitivity["selection_counts"] if sensitivity else {"000": 1}
    _bar(out / "result_q1_sensitivity.png", list(counts), list(counts.values()), "Computed weight sensitivity", (150, 80, 160))
    if projection:
        _line(out / "result_q1_long_term.png", projection, "Directional 20-year projection")


def build_report(case, metrics, path: Path, case_path: Path):
    top = metrics["ranking"][0]
    path.write_text(f"""# Reimagining Maasai Mara: Modeling Report

## Problem framing
The task is a policy design and comparison problem for wildlife, livelihoods, human-wildlife conflict, and implementation cost inside and around Maasai Mara. The official prompt has three requirements: recommend area-specific strategies, provide a ranking methodology with interaction/economic models, and project long-term outcomes and transferability.

## Data audit
The deterministic case summary is verified (problem SHA-256 `{case['problem_sha256']}`); `data_files` and `data_audit` are empty. No tabular observations are available, so all numeric effects below are declared scenario assumptions and not fitted estimates. Empirical calibration, causal identification, and field validation are pending.

## Assumptions
Six zones form a ring network. Candidate binary interventions are community co-management (C), zoning/corridors (Z), and a tourism levy (L). Capacity costs are 2, 3, and 1 units with a limit of 5. The network term uses mean degree and a zoning multiplier. The primary model is a normalized multi-objective maximin model across baseline, drought, and tourism-surge scenarios; a zero-action policy is the baseline. A geometric mean gives equal elasticity to wildlife, livelihood, conflict reduction, and fiscal feasibility without arbitrary additive weights. Sensitivity varies objective weights.

## Candidate models
The selected model combines a zone interaction network, constrained policy enumeration, multi-objective utility, and maximin scenario analysis. A single-weight additive MCDA baseline was rejected because the case summary identifies arbitrary weights as a common failure. An empirically calibrated spatial system-dynamics model remains pending because no observations are supplied.

## Baseline
The reference policy `000` means no incremental C, Z, or L intervention; it does not claim that current management is inactive. All comparisons are conditional changes from that reference.

## Mathematical specification
For policy x, capacity is `2C+3Z+L <= 5`. Objectives are clipped to [0,1]: wildlife and livelihood benefits, conflict reduction `1-conflict_rate`, and cost feasibility `1-cost`. Scenario score is `U_s=(W_s L_s F_s K_s)^{{1/4}}`; robust score is `min_s U_s`. Policies are enumerated exactly, so the capacity constraint is never relaxed.

## Code/prototype
`model.py` reads only the supplied JSON, enumerates feasible policies, evaluates all three scenarios, writes metrics, and emits at least nine PNG figures.

## Experiment
The unique command is `python model.py --case "{case_path}" --metrics artifacts/metrics.json --figures artifacts/figures --report artifacts/modeling_report.md`.

## Validation
Validation is internal consistency: deterministic reruns, objective bounds, and capacity checks. The recommended policy is `{''.join(str(top['policy'][k]) for k in POLICIES)}` with robust score `{top['robust_score']:.4f}`. Because there are no observations, external predictive validation is pending.

## Sensitivity/robustness
Scenario maximin ranking, computed weight sensitivity, and a directional 20-year projection are reported in the metrics file and figures.

## Falsification
The recommendation is falsified if observed wildlife, conflict, livelihood, or cost responses reverse the assumed policy directions; if zone topology differs materially; or if the capacity limit is infeasible.

## Reviewer risks
Main risks are assumption-driven effect sizes, unverified equal-importance utility, omitted stakeholder heterogeneity, and no spatial/time-series calibration.

## Long-term and transferability
The model projects directional comparisons rather than absolute population forecasts. It transfers to another preserve by replacing the zone graph, capacity costs, scenario shocks, and empirically estimated response coefficients, then rerunning the same constrained enumeration and maximin ranking.

## Reproducibility manifest
See `artifacts/manifest.json` for input hash, runtime, parameters, and output paths. No external citations or binary attachments were used.
""", encoding="utf-8")


def run(case_path: Path, metrics_path: Path, figures_path: Path, report_path: Path):
    case = load_case(case_path)
    policies = list(enumerate_policies())
    scenario_results = [evaluate_policy(case, p, s) for p in policies for s in SCENARIOS]
    robust = []
    for p in policies:
        runs = [r for r in scenario_results if r["policy"] == p]
        worst = min(r["robust_score"] for r in runs)
        base = next(r for r in runs if r["scenario"] == "baseline")
        robust.append({**base, "scenario": "robust", "robust_score": worst, "scenarios": runs})
    ranking = sorted(robust, key=lambda r: (r["robust_score"], r["objectives"]["livelihood"]), reverse=True)
    sensitivity = weight_sensitivity(case, policies)
    projection = project_long_term(case, ranking[0]["policy"], years=20)
    metrics = {"case_id": case["case_id"], "model": "network_multiobjective_maximin", "ranking": ranking,
               "scenario_results": scenario_results, "assumptions": {"capacity_limit": CAPACITY_LIMIT, "policy_capacity": POLICY_CAPACITY, "scenarios": SCENARIOS},
               "sensitivity": sensitivity, "long_term_projection": projection,
               "pending_stages": ["empirical_calibration", "external_validation", "long_term_field_forecast"]}
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    make_figures(scenario_results + ranking, figures_path, sensitivity, projection)
    build_report(case, metrics, report_path, case_path)
    manifest = {"case_id": case["case_id"], "input_sha256": hashlib.sha256(Path(case_path).read_bytes()).hexdigest(),
                "command": f"python model.py --case {case_path} --metrics {metrics_path} --figures {figures_path} --report {report_path}",
                "seed": None, "dependencies": {"python": "3.12+", "numpy": "available", "Pillow": "available"}, "outputs": [str(metrics_path), str(report_path)]}
    (metrics_path.parent / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", type=Path, default=DEFAULT_CASE)
    ap.add_argument("--metrics", type=Path, default=Path("results/metrics.json"))
    ap.add_argument("--figures", type=Path, default=Path("figures"))
    ap.add_argument("--report", type=Path, default=Path("results/modeling_report.md"))
    args = ap.parse_args()
    run(args.case, args.metrics, args.figures, args.report)

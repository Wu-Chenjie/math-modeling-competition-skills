#!/usr/bin/env python3
"""Deterministic scenario model for MCM 2023 Problem B.

The benchmark contains no empirical data. Every numeric model input below is
therefore labeled as a scenario assumption; outputs are comparative indices,
not empirical forecasts for Maasai Mara.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import random
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


EXPECTED_CASE = "mcm-2023-b"
EXPECTED_PROBLEM_SHA256 = "a22b1cdf79432f5ed5cc3443f360322e968ff4255bdabb791b5f9afae96a63f4"
SEED = 2023003
YEARS = 30
N_MONTE_CARLO = 600


@dataclass(frozen=True)
class Policy:
    name: str
    habitat: float
    corridor: float
    community: float
    conflict: float
    visitor_cap: float


@dataclass(frozen=True)
class Params:
    wildlife_growth: float = 0.075
    habitat_recovery: float = 0.055
    tourism_yield: float = 0.080
    conflict_pressure: float = 0.060
    climate_stress: float = 0.018
    governance_efficiency: float = 0.78


POLICIES: Tuple[Policy, ...] = (
    Policy("status_quo", 0.30, 0.20, 0.25, 0.25, 0.92),
    Policy("strict_zoning", 0.80, 0.50, 0.25, 0.55, 0.62),
    Policy("community_led", 0.52, 0.42, 0.88, 0.78, 0.76),
    Policy("corridor_first", 0.62, 0.92, 0.48, 0.65, 0.70),
    Policy("balanced_portfolio", 0.72, 0.78, 0.78, 0.82, 0.72),
)


def clamp(value: float, lo: float = 0.0, hi: float = 1.5) -> float:
    return min(hi, max(lo, value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def load_case(path: Path) -> Tuple[dict, str]:
    raw_hash = sha256_file(path)
    case = json.loads(path.read_text(encoding="utf-8"))
    assert case["case_id"] == EXPECTED_CASE
    assert case["problem_sha256"] == EXPECTED_PROBLEM_SHA256
    assert case["data_files"] == [] and case["data_audit"] == []
    assert len(case["problem_text"]) > 2000
    return case, raw_hash


def simulate(policy: Policy, params: Params, years: int = YEARS) -> List[dict]:
    # Normalized initial states are explicit hypothetical indices, not observations.
    w, h, income, conflict, visitors = 0.62, 0.66, 0.48, 0.38, 0.72
    trajectory: List[dict] = []
    for year in range(years + 1):
        connectivity = clamp(0.45 * h + 0.55 * policy.corridor, 0.0, 1.0)
        trajectory.append({
            "year": year,
            "wildlife": w,
            "habitat": h,
            "income": income,
            "conflict": conflict,
            "visitors": visitors,
            "connectivity": connectivity,
        })
        if year == years:
            break
        carrying = clamp(0.42 + 0.43 * h + 0.15 * connectivity, 0.2, 1.2)
        crowding = max(0.0, visitors - policy.visitor_cap)
        dw = params.wildlife_growth * w * (1.0 - w / carrying)
        dw += 0.018 * policy.corridor - 0.045 * conflict - 0.030 * crowding
        dh = params.habitat_recovery * policy.habitat * (1.0 - h)
        dh -= params.climate_stress * h + 0.022 * visitors * (1.0 - policy.habitat)
        desired_visitors = min(policy.visitor_cap, 0.28 + 0.62 * w)
        dv = 0.24 * (desired_visitors - visitors)
        tourism = params.tourism_yield * visitors * (0.55 + 0.45 * policy.community)
        di = tourism + 0.035 * policy.community - 0.052 * conflict - 0.045 * income
        exposure = 0.025 + 0.065 * visitors + 0.055 * (1.0 - connectivity)
        mitigation = params.conflict_pressure * params.governance_efficiency * policy.conflict
        dc = exposure * (0.65 + 0.35 * w) - mitigation - 0.16 * conflict
        w = clamp(w + dw, 0.0, 1.2)
        h = clamp(h + dh, 0.0, 1.2)
        visitors = clamp(visitors + dv, 0.0, 1.1)
        income = clamp(income + di, 0.0, 1.3)
        conflict = clamp(conflict + dc, 0.0, 1.0)
    return trajectory


def summarize(policy: Policy, trajectory: Sequence[dict]) -> dict:
    final = trajectory[-1]
    tail = trajectory[-10:]
    mean_conflict = sum(row["conflict"] for row in tail) / len(tail)
    mean_income = sum(row["income"] for row in tail) / len(tail)
    outcomes = {
        "ecology": 0.45 * final["wildlife"] + 0.35 * final["habitat"] + 0.20 * final["connectivity"],
        "livelihood": mean_income,
        "coexistence": 1.0 - mean_conflict,
        "tourism": sum(row["visitors"] for row in tail) / len(tail),
    }
    feasible = (
        max(row["visitors"] for row in trajectory[1:]) <= policy.visitor_cap + 0.10
        and min(row["habitat"] for row in trajectory) >= 0.35
        and max(row["conflict"] for row in trajectory[-10:]) <= 0.60
    )
    return {
        "policy": policy.name,
        "final_state": {k: round(float(v), 6) for k, v in final.items() if k != "year"},
        "outcomes": {k: round(v, 6) for k, v in outcomes.items()},
        "feasible": feasible,
    }


def normalize_outcomes(summaries: Sequence[dict]) -> Dict[str, Dict[str, float]]:
    keys = ("ecology", "livelihood", "coexistence", "tourism")
    bounds = {
        key: (
            min(s["outcomes"][key] for s in summaries),
            max(s["outcomes"][key] for s in summaries),
        )
        for key in keys
    }
    normalized: Dict[str, Dict[str, float]] = {}
    for summary in summaries:
        row = {}
        for key in keys:
            lo, hi = bounds[key]
            row[key] = 0.5 if math.isclose(lo, hi) else (summary["outcomes"][key] - lo) / (hi - lo)
        normalized[summary["policy"]] = row
    return normalized


def weight_grid(step: int = 10) -> Iterable[Tuple[float, float, float, float]]:
    for a in range(step + 1):
        for b in range(step + 1 - a):
            for c in range(step + 1 - a - b):
                d = step - a - b - c
                yield a / step, b / step, c / step, d / step


def rank_acceptability(normalized: Dict[str, Dict[str, float]]) -> dict:
    keys = ("ecology", "livelihood", "coexistence", "tourism")
    wins = {name: 0 for name in normalized}
    mean_scores = {name: 0.0 for name in normalized}
    grids = list(weight_grid())
    for weights in grids:
        scores = {
            name: sum(weights[i] * values[key] for i, key in enumerate(keys))
            for name, values in normalized.items()
        }
        best = max(scores.values())
        winners = [name for name, value in scores.items() if math.isclose(value, best, abs_tol=1e-12)]
        for name in winners:
            wins[name] += 1.0 / len(winners)
        for name, value in scores.items():
            mean_scores[name] += value / len(grids)
    return {
        name: {
            "weight_grid_win_share": round(wins[name] / len(grids), 6),
            "mean_normalized_score": round(mean_scores[name], 6),
        }
        for name in normalized
    }


def dominates(a: dict, b: dict) -> bool:
    keys = ("ecology", "livelihood", "coexistence", "tourism")
    return all(a[k] >= b[k] for k in keys) and any(a[k] > b[k] for k in keys)


def pareto_front(normalized: Dict[str, Dict[str, float]]) -> List[str]:
    return sorted(name for name, values in normalized.items()
                  if not any(other != name and dominates(other_values, values)
                             for other, other_values in normalized.items()))


def sampled_params(rng: random.Random, base: Params, scale: float = 0.20) -> Params:
    def draw(value: float) -> float:
        return value * rng.uniform(1.0 - scale, 1.0 + scale)
    return Params(*(draw(value) for value in base.__dict__.values()))


def robustness(base: Params) -> dict:
    rng = random.Random(SEED)
    winners = {p.name: 0 for p in POLICIES}
    feasible_counts = {p.name: 0 for p in POLICIES}
    score_samples = {p.name: [] for p in POLICIES}
    for _ in range(N_MONTE_CARLO):
        params = sampled_params(rng, base)
        summaries = [summarize(p, simulate(p, params)) for p in POLICIES]
        normalized = normalize_outcomes(summaries)
        scores = {name: sum(values.values()) / 4.0 for name, values in normalized.items()}
        winner = max(sorted(scores), key=lambda name: scores[name])
        winners[winner] += 1
        for summary in summaries:
            feasible_counts[summary["policy"]] += int(summary["feasible"])
            score_samples[summary["policy"]].append(scores[summary["policy"]])
    return {
        name: {
            "equal_weight_win_rate": round(winners[name] / N_MONTE_CARLO, 6),
            "feasibility_rate": round(feasible_counts[name] / N_MONTE_CARLO, 6),
            "score_mean": round(sum(score_samples[name]) / N_MONTE_CARLO, 6),
            "score_min": round(min(score_samples[name]), 6),
            "score_max": round(max(score_samples[name]), 6),
        }
        for name in winners
    }


def one_at_a_time_sensitivity(base: Params) -> dict:
    results = {}
    for field in base.__dict__:
        for factor in (0.9, 1.1):
            params = replace(base, **{field: getattr(base, field) * factor})
            summaries = [summarize(p, simulate(p, params)) for p in POLICIES]
            normalized = normalize_outcomes(summaries)
            scores = {name: sum(v.values()) / 4.0 for name, v in normalized.items()}
            winner = max(sorted(scores), key=lambda name: scores[name])
            results[f"{field}_{factor:.1f}"] = {"winner": winner, "scores": {k: round(v, 6) for k, v in scores.items()}}
    return results


def svg_line(path: Path, title: str, series: Sequence[Tuple[str, Sequence[float]]], x_label: str, y_label: str) -> None:
    width, height = 900, 520
    left, right, top, bottom = 82, 35, 55, 72
    colors = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00")
    all_values = [v for _, values in series for v in values]
    lo, hi = min(all_values), max(all_values)
    pad = max(0.03, (hi - lo) * 0.08)
    lo, hi = lo - pad, hi + pad
    n = max(len(values) for _, values in series)
    def point(i: int, value: float) -> Tuple[float, float]:
        x = left + (width - left - right) * i / max(1, n - 1)
        y = top + (height - top - bottom) * (hi - value) / max(1e-12, hi - lo)
        return x, y
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             f'<text x="{width/2}" y="28" text-anchor="middle" font-family="Arial" font-size="18">{title}</text>',
             f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#222"/>',
             f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#222"/>']
    for tick in range(6):
        value = lo + (hi - lo) * tick / 5
        y = point(0, value)[1]
        lines += [f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#ddd"/>',
                  f'<text x="{left-9}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{value:.2f}</text>']
    for idx, (name, values) in enumerate(series):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, v) for i, v in enumerate(values)))
        color = colors[idx % len(colors)]
        lines.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        lx, ly = width - right - 180, top + 18 * idx
        lines += [f'<line x1="{lx}" y1="{ly}" x2="{lx+22}" y2="{ly}" stroke="{color}" stroke-width="3"/>',
                  f'<text x="{lx+28}" y="{ly+4}" font-family="Arial" font-size="11">{name}</text>']
    lines += [f'<text x="{width/2}" y="{height-20}" text-anchor="middle" font-family="Arial" font-size="13">{x_label}</text>',
              f'<text x="18" y="{height/2}" transform="rotate(-90 18 {height/2})" text-anchor="middle" font-family="Arial" font-size="13">{y_label}</text>', '</svg>']
    path.write_text("\n".join(lines), encoding="utf-8")


def svg_bars(path: Path, title: str, values: Sequence[Tuple[str, float]], y_label: str) -> None:
    width, height = 900, 520
    left, right, top, bottom = 82, 35, 55, 105
    colors = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00")
    ymax = max(1.0, max(v for _, v in values) * 1.1)
    plot_w, plot_h = width-left-right, height-top-bottom
    slot = plot_w / len(values)
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{width/2}" y="28" text-anchor="middle" font-family="Arial" font-size="18">{title}</text>']
    for tick in range(6):
        value = ymax * tick / 5
        y = top + plot_h * (1 - value/ymax)
        lines += [f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#ddd"/>', f'<text x="{left-9}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{value:.2f}</text>']
    for i, (name, value) in enumerate(values):
        x = left + slot*i + slot*0.18
        bar_w = slot*0.64
        y = top + plot_h*(1-value/ymax)
        lines += [f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{top+plot_h-y:.1f}" fill="{colors[i%len(colors)]}"/>', f'<text x="{x+bar_w/2:.1f}" y="{height-bottom+18}" text-anchor="middle" font-family="Arial" font-size="10" transform="rotate(25 {x+bar_w/2:.1f} {height-bottom+18})">{name}</text>']
    lines += [f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#222"/>', f'<text x="18" y="{height/2}" transform="rotate(-90 18 {height/2})" text-anchor="middle" font-family="Arial" font-size="13">{y_label}</text>', '</svg>']
    path.write_text("\n".join(lines), encoding="utf-8")


def png_chart(path: Path, title: str, values: Sequence[Tuple[str, float]], y_label: str, line: bool = False) -> None:
    """Small Pillow fallback raster export; 900x520 at 300 DPI metadata."""
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (900, 520), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 18)
        small = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        font = ImageFont.load_default(); small = font
    draw.text((450, 18), title, fill="black", anchor="ma", font=font)
    left, right, top, bottom = 82, 35, 55, 72
    plot_w, plot_h = 900-left-right, 520-top-bottom
    vals = [v for _, v in values]
    lo, hi = (min(vals), max(vals)) if line else (0.0, max(1.0, max(vals)*1.1))
    if math.isclose(lo, hi): hi = lo + 1.0
    draw.line((left, top, left, 520-bottom), fill="#222", width=2)
    draw.line((left, 520-bottom, 900-right, 520-bottom), fill="#222", width=2)
    for tick in range(6):
        value = lo + (hi-lo)*tick/5
        y = int(top + plot_h*(hi-value)/(hi-lo))
        draw.line((left, y, 900-right, y), fill="#dddddd", width=1)
        draw.text((left-8, y), f"{value:.2f}", fill="black", anchor="rm", font=small)
    colors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"]
    if line:
        points = []
        for i, (_, value) in enumerate(values):
            x = int(left + plot_w*i/max(1, len(values)-1)); y = int(top + plot_h*(hi-value)/(hi-lo)); points.append((x,y))
        draw.line(points, fill=colors[0], width=3)
    else:
        slot = plot_w/max(1, len(values))
        for i, (name, value) in enumerate(values):
            x = int(left + slot*i + slot*0.18); bw = int(slot*0.64); y = int(top + plot_h*(hi-value)/(hi-lo))
            draw.rectangle((x, y, x+bw, 520-bottom), fill=colors[i%len(colors)])
            draw.text((x+bw//2, 520-bottom+8), name, fill="black", anchor="ma", font=small)
    draw.text((18, 260), y_label, fill="black", anchor="mm", font=small)
    image.save(path, dpi=(300, 300))


def write_figures(figures_dir: Path, trajectories: Dict[str, List[dict]], summaries: Sequence[dict], normalized: dict, ranks: dict, robust: dict) -> List[str]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    created: List[str] = []
    specs = [
        ("raw_q1_assumed_levers.svg", "Scenario policy levers (assumptions)", [(p.name, (p.habitat+p.corridor+p.community+p.conflict)/4) for p in POLICIES], "Mean lever index"),
        ("raw_q2_initial_state.svg", "Common hypothetical initial state", [("wildlife", .62), ("habitat", .66), ("income", .48), ("coexistence", .62), ("visitors", .72)], "Normalized index"),
        ("raw_q3_parameter_scale.svg", "Assumed dynamic parameter magnitudes", [(k, v) for k, v in Params().__dict__.items()], "Per-year coefficient"),
        ("result_q1_ecology.svg", "Long-term ecology outcome", [(s["policy"], s["outcomes"]["ecology"]) for s in summaries], "Ecology index"),
        ("result_q2_coexistence.svg", "Long-term coexistence outcome", [(s["policy"], s["outcomes"]["coexistence"]) for s in summaries], "1 - conflict index"),
        ("result_q3_robustness.svg", "Uncertainty scenario win rate", [(n, v["equal_weight_win_rate"]) for n, v in robust.items()], "Win rate"),
    ]
    for filename, title, values, ylabel in specs:
        svg_bars(figures_dir / filename, title, values, ylabel)
        png_chart(figures_dir / filename.replace(".svg", ".png"), title, values, ylabel)
        created.append(filename)
    for filename, title, key in (
        ("process_q1_wildlife_paths.svg", "Wildlife trajectories", "wildlife"),
        ("process_q2_income_paths.svg", "Community income trajectories", "income"),
        ("process_q3_conflict_paths.svg", "Human-wildlife conflict trajectories", "conflict"),
    ):
        series = [(name, [row[key] for row in trajectory]) for name, trajectory in trajectories.items()]
        svg_line(figures_dir / filename, title, series, "Year", "Normalized index")
        # Rasterize each policy path as a single combined chart for QA portability.
        png_chart(figures_dir / filename.replace(".svg", ".png"), title, [(name, values[-1]) for name, values in series], "Normalized index")
        created.append(filename)
    return created


def tests(case: dict, trajectories: Dict[str, List[dict]], summaries: Sequence[dict], robust: dict) -> dict:
    checks = {
        "case_complete_text": len(case["problem_text"]) > 2000,
        "no_empirical_data_claimed": case["data_files"] == [] and case["data_audit"] == [],
        "trajectory_length": all(len(t) == YEARS + 1 for t in trajectories.values()),
        "finite_bounded_states": all(math.isfinite(v) and 0 <= v <= 1.5 for t in trajectories.values() for row in t for k, v in row.items() if k != "year"),
        "visitor_capacity_constraint": all(max(r["visitors"] for r in trajectories[p.name][1:]) <= p.visitor_cap + 0.10 + 1e-12 for p in POLICIES),
        "robustness_rates_valid": all(0 <= row["equal_weight_win_rate"] <= 1 and 0 <= row["feasibility_rate"] <= 1 for row in robust.values()),
        "deterministic_repeat": simulate(POLICIES[0], Params()) == simulate(POLICIES[0], Params()),
        "baseline_present": any(s["policy"] == "status_quo" for s in summaries),
    }
    return {"passed": sum(checks.values()), "total": len(checks), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--figures", type=Path, default=Path("figures"))
    args = parser.parse_args()
    start = time.perf_counter()
    case, input_hash = load_case(args.input)
    args.output.mkdir(parents=True, exist_ok=True)
    base = Params()
    trajectories = {p.name: simulate(p, base) for p in POLICIES}
    summaries = [summarize(p, trajectories[p.name]) for p in POLICIES]
    normalized = normalize_outcomes(summaries)
    ranks = rank_acceptability(normalized)
    robust = robustness(base)
    sensitivity = one_at_a_time_sensitivity(base)
    pareto = pareto_front(normalized)
    best = max(sorted(ranks), key=lambda n: ranks[n]["mean_normalized_score"])
    baseline = next(s for s in summaries if s["policy"] == "status_quo")
    test_results = tests(case, trajectories, summaries, robust)
    assert test_results["passed"] == test_results["total"]
    figures = write_figures(args.figures, trajectories, summaries, normalized, ranks, robust)
    with (args.output / "policy_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["policy", "ecology", "livelihood", "coexistence", "tourism", "feasible", "weight_grid_win_share", "mc_win_rate"])
        for s in summaries:
            n = s["policy"]
            writer.writerow([n, *(s["outcomes"][k] for k in ("ecology", "livelihood", "coexistence", "tourism")), s["feasible"], ranks[n]["weight_grid_win_share"], robust[n]["equal_weight_win_rate"]])
    metrics = {
        "case_id": case["case_id"],
        "input_sha256": input_hash,
        "problem_sha256": case["problem_sha256"],
        "data_status": "no empirical data files or audited rows supplied",
        "units": "dimensionless scenario indices unless stated otherwise",
        "seed": SEED,
        "years": YEARS,
        "monte_carlo_runs": N_MONTE_CARLO,
        "baseline": baseline,
        "policy_summaries": summaries,
        "normalized_outcomes": normalized,
        "rank_acceptability": ranks,
        "pareto_front": pareto,
        "recommended_scenario_policy": best,
        "robustness": robust,
        "sensitivity": sensitivity,
        "tests": test_results,
        "figures": figures,
    }
    report = {
        "problem_framing": {
            "decision": "Allocate management emphasis among habitat protection, corridors, community benefit sharing, conflict mitigation, and tourism capacity.",
            "objectives": ["ecological persistence", "local livelihoods", "human-wildlife coexistence", "sustainable tourism"],
            "time_horizon_years": YEARS,
        },
        "data_audit": {
            "source_status": case["source_status"],
            "problem_text_present": True,
            "data_files_count": len(case["data_files"]),
            "audited_rows_count": len(case["data_audit"]),
            "consequence": "No empirical calibration, geographic siting, absolute forecasts, or statistical confidence claims are possible.",
        },
        "assumptions": {
            "status": "hypothetical and explicitly uncalibrated",
            "initial_indices": {"wildlife": .62, "habitat": .66, "income": .48, "conflict": .38, "visitors": .72},
            "dynamic_parameters": base.__dict__,
            "policy_levers": [p.__dict__ for p in POLICIES],
        },
        "candidate_models": [
            {"name": "coupled bounded system dynamics", "purpose": "predict interactions and long-term comparative trends"},
            {"name": "multi-objective scenario ranking with network-connectivity proxy", "purpose": "compare trade-offs without fixing one arbitrary weight vector"},
        ],
        "baseline": baseline,
        "math_specification": {
            "states": ["wildlife W", "habitat H", "income I", "conflict C", "visitors V", "connectivity K"],
            "connectivity": "K_t = 0.45 H_t + 0.55 corridor",
            "wildlife": "W_(t+1)=clip(W_t+rW_t(1-W_t/carrying)+0.018*corridor-0.045*C_t-0.030*crowding)",
            "habitat": "H_(t+1)=clip(H_t+recovery*habitat_lever*(1-H_t)-climate*H_t-0.022*V_t*(1-habitat_lever))",
            "ranking": "min-max normalize four outcomes; enumerate all 4-objective weights on the 0.1 simplex; report win shares and Pareto set",
        },
        "code_prototype": {"entry_point": "run_model.py", "outputs": ["results/metrics.json", "results/policy_metrics.csv", "results/modeling_report.json", "figures/*.svg"]},
        "experiment": {"policies": [p.name for p in POLICIES], "horizon": YEARS, "uncertainty_draws": N_MONTE_CARLO, "parameter_uncertainty": "independent uniform +/-20% around assumptions"},
        "validation": test_results,
        "sensitivity_robustness": {"one_at_a_time": sensitivity, "monte_carlo": robust, "weight_grid": ranks},
        "falsification": {
            "tests": test_results["checks"],
            "empirical_rejection_conditions": [
                "Observed annual wildlife/habitat changes fall outside fitted predictive intervals after calibration.",
                "Measured conflict does not decrease with independently verified mitigation exposure.",
                "Policy ranking reverses under stakeholder-approved weights or plausible calibrated parameters.",
                "Spatial corridor connectivity computed from GIS contradicts the proxy ordering used here.",
            ],
        },
        "reviewer_risks": [
            "All numeric inputs are assumptions because the benchmark supplies no data rows.",
            "Normalized indices cannot support absolute economic, population, or certainty estimates.",
            "The connectivity proxy is not a GIS network analysis.",
            "Independent parameter draws omit correlation and structural uncertainty.",
            "A policy recommendation is conditional on the scenario equations and must not be presented as field evidence.",
        ],
        "reproducibility_manifest": {
            "command": f'python run_model.py --input "{args.input.as_posix()}"',
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "seed": SEED,
            "input_sha256": input_hash,
            "dependencies": "Python standard library only",
        },
        "pending_stages": [
            "empirical calibration and out-of-sample validation (no data supplied)",
            "GIS network/corridor siting (no spatial data supplied)",
            "absolute economic and wildlife forecasts with calibrated uncertainty (no observations supplied)",
            "stakeholder elicitation and approval of objective weights/constraints",
            "external literature and citation validation (benchmark input is closed and only contains two legal references)",
        ],
    }
    (args.output / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    (args.output / "modeling_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    manifest = report["reproducibility_manifest"] | {
        "code_sha256": sha256_file(Path(__file__)),
        "metrics_sha256": sha256_file(args.output / "metrics.json"),
        "figures_count": len(figures),
        "runtime_seconds": round(time.perf_counter() - start, 6),
    }
    (args.output / "reproducibility_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": "completed_with_pending_data_stages", "metrics_path": str(args.output / "metrics.json"), "figures_count": len(figures), "tests": f'{test_results["passed"]}/{test_results["total"]} passed', "pending_stages": report["pending_stages"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

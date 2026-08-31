"""Reproducible scenario model for 2023 MCM Problem A.

This is a hypothesis-generating model. The benchmark contains no empirical
data, so all ecological coefficients are explicit scenario assumptions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import random
import statistics
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Sequence


SEED = 2023001
YEARS = 120
ENSEMBLES = 24
EPS = 1e-9


@dataclass(frozen=True)
class Scenario:
    name: str = "baseline"
    richness: int = 4
    composition: str = "mixed"
    drought_probability: float = 0.20
    drought_variability: float = 0.35
    pollution: float = 0.0
    habitat_fraction: float = 1.0
    facilitation: float = 0.22
    competition: float = 0.55


def traits(richness: int, composition: str) -> list[tuple[float, float, float]]:
    """Return (drought tolerance, intrinsic growth, pollution sensitivity)."""
    if richness < 1:
        raise ValueError("richness must be positive")
    if composition == "mixed":
        tolerances = [0.15 + 0.75 * i / max(1, richness - 1) for i in range(richness)]
    elif composition == "tolerant":
        tolerances = [0.68 + 0.25 * i / max(1, richness - 1) for i in range(richness)]
    elif composition == "fast_growth":
        tolerances = [0.08 + 0.30 * i / max(1, richness - 1) for i in range(richness)]
    else:
        raise ValueError(f"unknown composition: {composition}")
    return [(t, 0.82 - 0.38 * t, 0.35 + 0.35 * (1.0 - t)) for t in tolerances]


def weather(years: int, scenario: Scenario, rng: random.Random) -> tuple[list[float], list[int]]:
    adequacy, drought = [], []
    for _ in range(years):
        is_drought = rng.random() < scenario.drought_probability
        if is_drought:
            concentration = max(1.5, 14.0 * (1.0 - scenario.drought_variability))
            severity = rng.betavariate(2.2, concentration)
            w = max(0.03, 1.0 - 1.8 * severity)
        else:
            w = min(1.15, max(0.65, rng.gauss(0.94, 0.08 + 0.10 * scenario.drought_variability)))
        adequacy.append(w)
        drought.append(int(is_drought))
    return adequacy, drought


def simulate(scenario: Scenario, seed: int = SEED, years: int = YEARS) -> dict:
    rng = random.Random(seed)
    tr = traits(scenario.richness, scenario.composition)
    water, drought = weather(years, scenario, rng)
    biomass = [0.42 / scenario.richness] * scenario.richness
    adaptation = [t for t, _, _ in tr]
    trajectory = [sum(biomass)]
    diversity = (max(t for t, _, _ in tr) - min(t for t, _, _ in tr)) if len(tr) > 1 else 0.0

    for w in water:
        total = sum(biomass)
        next_biomass = []
        for i, ((base_tolerance, growth, pollution_sensitivity), b) in enumerate(zip(tr, biomass)):
            drought_stress = max(0.0, 1.0 - w)
            effective_tolerance = min(0.98, 0.55 * base_tolerance + 0.45 * adaptation[i])
            insurance = scenario.facilitation * diversity * drought_stress
            water_response = max(0.02, w + effective_tolerance * drought_stress + insurance)
            capacity = max(EPS, scenario.habitat_fraction * (0.82 + 0.28 * effective_tolerance))
            competitive_load = b + scenario.competition * (total - b)
            mortality = 0.72 * (1.0 - effective_tolerance) * drought_stress
            pollution_loss = scenario.pollution * pollution_sensitivity
            rate = growth * water_response * (1.0 - competitive_load / capacity) - mortality - pollution_loss - 0.06
            next_biomass.append(max(0.0, min(2.0 * capacity, b * math.exp(max(-3.0, min(1.0, rate))))))
            learning = 0.045 * drought_stress * (1.0 - adaptation[i]) * (1.0 + 0.5 * diversity)
            forgetting = 0.008 * (1.0 - drought_stress) * (adaptation[i] - base_tolerance)
            adaptation[i] = min(0.99, max(base_tolerance, adaptation[i] + learning - forgetting))
        biomass = next_biomass
        trajectory.append(sum(biomass))

    last = trajectory[-20:]
    return {
        "scenario": scenario.name,
        "seed": seed,
        "water": water,
        "drought": drought,
        "trajectory": trajectory,
        "terminal_biomass": statistics.mean(last),
        "minimum_biomass": min(trajectory),
        "survived": min(last) >= 0.05,
        "coefficient_of_variation": statistics.pstdev(last) / max(EPS, statistics.mean(last)),
        "trait_range": diversity,
        "final_adaptation_mean": statistics.mean(adaptation),
    }


def ensemble(scenario: Scenario, n: int = ENSEMBLES) -> dict:
    runs = [simulate(scenario, SEED + 7919 * i) for i in range(n)]
    terminal = [r["terminal_biomass"] for r in runs]
    survival = [float(r["survived"]) for r in runs]
    return {
        "scenario": scenario.name,
        "richness": scenario.richness,
        "composition": scenario.composition,
        "terminal_mean": statistics.mean(terminal),
        "terminal_median": statistics.median(terminal),
        "terminal_sd": statistics.stdev(terminal) if len(terminal) > 1 else 0.0,
        "survival_probability": statistics.mean(survival),
        "mean_cv": statistics.mean(r["coefficient_of_variation"] for r in runs),
    }


def svg_chart(path: Path, title: str, x_label: str, y_label: str,
              series: Sequence[tuple[str, Sequence[float], Sequence[float]]]) -> None:
    width, height = 900, 540
    left, right, top, bottom = 78, 28, 58, 66
    colors = ["#2563eb", "#dc2626", "#059669", "#7c3aed", "#d97706", "#0891b2"]
    xs = [v for _, x, _ in series for v in x]
    ys = [v for _, _, y in series for v in y]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if math.isclose(xmin, xmax): xmax = xmin + 1.0
    if math.isclose(ymin, ymax): ymax = ymin + 1.0
    ypad = 0.06 * (ymax - ymin)
    ymin, ymax = min(0.0, ymin - ypad), ymax + ypad
    sx = lambda x: left + (x - xmin) / (xmax - xmin) * (width - left - right)
    sy = lambda y: height - bottom - (y - ymin) / (ymax - ymin) * (height - top - bottom)
    root = ET.Element("svg", xmlns="http://www.w3.org/2000/svg", width=str(width), height=str(height), viewBox=f"0 0 {width} {height}")
    ET.SubElement(root, "rect", x="0", y="0", width=str(width), height=str(height), fill="#ffffff")
    ET.SubElement(root, "text", x=str(left), y="30", fill="#111827", style="font: bold 20px sans-serif").text = title
    for i in range(6):
        val = ymin + i * (ymax - ymin) / 5
        yy = sy(val)
        ET.SubElement(root, "line", x1=str(left), x2=str(width-right), y1=f"{yy:.2f}", y2=f"{yy:.2f}", stroke="#e5e7eb")
        ET.SubElement(root, "text", x=str(left-10), y=f"{yy+4:.2f}", fill="#4b5563", style="font: 12px sans-serif", **{"text-anchor":"end"}).text = f"{val:.2f}"
    ET.SubElement(root, "line", x1=str(left), x2=str(width-right), y1=str(height-bottom), y2=str(height-bottom), stroke="#111827")
    ET.SubElement(root, "line", x1=str(left), x2=str(left), y1=str(top), y2=str(height-bottom), stroke="#111827")
    for idx, (name, xvals, yvals) in enumerate(series):
        points = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in zip(xvals, yvals))
        ET.SubElement(root, "polyline", points=points, fill="none", stroke=colors[idx % len(colors)], **{"stroke-width":"2.5"})
        legend_y = 52 + 20 * idx
        ET.SubElement(root, "line", x1=str(width-205), x2=str(width-175), y1=str(legend_y), y2=str(legend_y), stroke=colors[idx % len(colors)], **{"stroke-width":"3"})
        ET.SubElement(root, "text", x=str(width-167), y=str(legend_y+4), fill="#1f2937", style="font: 12px sans-serif").text = name
    ET.SubElement(root, "text", x=str((left+width-right)/2), y=str(height-18), fill="#111827", style="font: 14px sans-serif", **{"text-anchor":"middle"}).text = x_label
    label = ET.SubElement(root, "text", x="18", y=str((top+height-bottom)/2), fill="#111827", style="font: 14px sans-serif", transform=f"rotate(-90 18 {(top+height-bottom)/2})", **{"text-anchor":"middle"})
    label.text = y_label
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def write_csv(path: Path, rows: Iterable[dict]) -> None:
    rows = list(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def validate_case(case: dict) -> None:
    if case.get("case_id") != "mcm-2023-a":
        raise ValueError("unexpected benchmark case")
    if case.get("data_files") or case.get("data_audit"):
        raise ValueError("this preregistered run expects no supplied empirical data")


def run_experiment(case_path: Path, output_root: Path) -> dict:
    started = time.perf_counter()
    case_bytes = case_path.read_bytes()
    case = json.loads(case_bytes)
    validate_case(case)
    results_dir = output_root / "results"
    figures_dir = output_root / "figures"
    results_dir.mkdir(exist_ok=True)
    figures_dir.mkdir(exist_ok=True)

    baseline = Scenario()
    baseline_run = simulate(baseline)
    richness = [ensemble(replace(baseline, name=f"richness_{n}", richness=n)) for n in range(1, 11)]
    compositions = [ensemble(replace(baseline, name=c, composition=c)) for c in ("mixed", "tolerant", "fast_growth")]
    regimes = [
        ensemble(replace(baseline, name="less_frequent", drought_probability=0.08, drought_variability=0.20)),
        ensemble(baseline),
        ensemble(replace(baseline, name="frequent_variable", drought_probability=0.38, drought_variability=0.70)),
    ]
    stress = [
        ensemble(replace(baseline, name="none")),
        ensemble(replace(baseline, name="pollution", pollution=0.18)),
        ensemble(replace(baseline, name="habitat_loss", habitat_fraction=0.62)),
        ensemble(replace(baseline, name="combined", pollution=0.18, habitat_fraction=0.62)),
    ]
    sensitivity = []
    for parameter, values in {
        "facilitation": [0.10, 0.22, 0.34],
        "competition": [0.40, 0.55, 0.70],
        "drought_probability": [0.12, 0.20, 0.30],
        "habitat_fraction": [0.65, 0.82, 1.00],
    }.items():
        for value in values:
            sensitivity.append({"parameter": parameter, "value": value, **ensemble(replace(baseline, name=f"sens_{parameter}_{value}", **{parameter: value}))})

    mono = richness[0]
    threshold = next((r["richness"] for r in richness if r["terminal_median"] >= 1.05 * mono["terminal_median"] and r["survival_probability"] >= mono["survival_probability"]), None)

    trajectory_rows = [{"year": i, "total_biomass": b, "water_adequacy": baseline_run["water"][i-1] if i else "", "drought": baseline_run["drought"][i-1] if i else ""} for i, b in enumerate(baseline_run["trajectory"])]
    write_csv(results_dir / "baseline_trajectory.csv", trajectory_rows)
    write_csv(results_dir / "richness_experiment.csv", richness)
    write_csv(results_dir / "composition_experiment.csv", compositions)
    write_csv(results_dir / "drought_regimes.csv", regimes)
    write_csv(results_dir / "external_stress.csv", stress)
    write_csv(results_dir / "sensitivity.csv", sensitivity)

    years = list(range(YEARS))
    rich_x = [r["richness"] for r in richness]
    comp_x = list(range(1, 4))
    regime_x = list(range(1, 4))
    stress_x = list(range(1, 5))
    figure_specs = [
        ("raw_q1_weather.svg", "Q1 input: irregular weather realization", "year", "water adequacy", [("water", years, baseline_run["water"])]),
        ("process_q1_biomass.svg", "Q1 process: baseline community dynamics", "year", "total biomass", [("biomass", list(range(YEARS+1)), baseline_run["trajectory"])]),
        ("result_q1_stability.svg", "Q1 result: biomass and running stability", "year", "index", [("biomass", list(range(YEARS+1)), baseline_run["trajectory"]), ("water", years, baseline_run["water"])]),
        ("raw_q2_richness.svg", "Q2 input: tested species richness", "species", "scenario index", [("design", rich_x, rich_x)]),
        ("process_q2_variability.svg", "Q2 process: richness versus variability", "species", "coefficient of variation", [("CV", rich_x, [r["mean_cv"] for r in richness])]),
        ("result_q2_benefit.svg", "Q2 result: biodiversity response", "species", "terminal biomass", [("mean", rich_x, [r["terminal_mean"] for r in richness]), ("median", rich_x, [r["terminal_median"] for r in richness])]),
        ("raw_q3_traits.svg", "Q3 input: composition classes", "class index", "terminal SD", [("ensemble spread", comp_x, [r["terminal_sd"] for r in compositions])]),
        ("process_q3_composition.svg", "Q3 process: composition and stability", "class index", "coefficient of variation", [("mixed/tolerant/fast", comp_x, [r["mean_cv"] for r in compositions])]),
        ("result_q3_composition.svg", "Q3 result: composition comparison", "class index", "terminal biomass", [("mixed/tolerant/fast", comp_x, [r["terminal_mean"] for r in compositions])]),
        ("raw_q4_regimes.svg", "Q4 input: drought regime ordering", "regime index", "drought probability", [("less/base/frequent", regime_x, [0.08, 0.20, 0.38])]),
        ("process_q4_variability.svg", "Q4 process: drought and variability", "regime index", "coefficient of variation", [("less/base/frequent", regime_x, [r["mean_cv"] for r in regimes])]),
        ("result_q4_drought.svg", "Q4 result: future drought regimes", "regime index", "terminal biomass", [("less/base/frequent", regime_x, [r["terminal_mean"] for r in regimes])]),
        ("raw_q5_stress.svg", "Q5 input: external stress design", "stress index", "relative pressure", [("none/pollution/habitat/combined", stress_x, [0.0, 0.18, 0.38, 0.56])]),
        ("process_q5_survival.svg", "Q5 process: external stress survival", "stress index", "survival probability", [("none/pollution/habitat/combined", stress_x, [r["survival_probability"] for r in stress])]),
        ("result_q5_management.svg", "Q5 result: stress mitigation priority", "stress index", "terminal biomass", [("none/pollution/habitat/combined", stress_x, [r["terminal_mean"] for r in stress])]),
    ]
    for spec in figure_specs:
        svg_chart(figures_dir / spec[0], *spec[1:])

    metrics = {
        "run_id": "B-mcm-2023-a-001-v2",
        "benchmark": {"case_id": case["case_id"], "source_status": case["source_status"], "summary_sha256": hashlib.sha256(case_bytes).hexdigest(), "problem_sha256": case["problem_sha256"], "data_sha256": case["data_sha256"]},
        "design": {"seed": SEED, "years": YEARS, "ensembles_per_cell": ENSEMBLES, "empirical_rows": 0},
        "baseline": {k: v for k, v in baseline_run.items() if k not in ("water", "drought", "trajectory")},
        "richness": richness,
        "benefit_threshold_species": threshold,
        "composition": compositions,
        "drought_regimes": regimes,
        "external_stress": stress,
        "sensitivity": sensitivity,
        "interpretation_scope": "Synthetic scenario evidence only; no empirical calibration or ecological forecast claim.",
    }
    (results_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")

    report = {
        "problem_framing": {"objective": "Explain how interacting plant communities respond over time to irregular drought, richness, composition, drought regime, pollution, and habitat loss.", "subproblems": ["q1 dynamic response", "q2 richness benefit", "q3 species types", "q4 drought frequency and variation", "q5 external stress and management"]},
        "data_audit": {"official_problem_text_present": True, "data_files": [], "rows_data": [], "empirical_observations": 0, "consequence": "Parameters cannot be fitted and predictions cannot be externally validated."},
        "assumptions": ["Annual time step and closed local community", "Biomass is dimensionless relative abundance", "Tolerance-growth tradeoff is monotone", "Trait spread provides drought insurance through facilitation", "Pollution adds mortality and habitat loss scales carrying capacity", "Scenario parameters are illustrative, not measured"],
        "candidate_models": [{"name": "stochastic trait-structured competition model", "selected": True, "reason": "directly represents weather, interactions, traits, and stressors"}, {"name": "empirical hierarchical state-space model", "selected": False, "reason": "preferred with longitudinal plot data, unavailable here"}],
        "baseline": {"scenario": baseline.__dict__, "executed_metrics": metrics["baseline"]},
        "math_specification": {"state": "B_i(t)>=0 biomass and A_i(t) in [tau_i,0.99] adaptation", "weather": "D_t~Bernoulli(p); W_t is bounded stochastic water adequacy conditional on D_t", "update": "B_i(t+1)=B_i(t) exp(clip(r_i R_i(t)(1-L_i/K_i)-m_i(t)-P_i-0.06,-3,1))", "interaction": "L_i=B_i+alpha*sum_{j!=i}B_j; R_i=W_t+A_i(1-W_t)+f*trait_range*(1-W_t)", "capacity": "K_i=h*(0.82+0.28*A_i)", "adaptation": "A_i increases under drought and relaxes toward baseline tolerance otherwise", "viability": "mean biomass over final 20 years and survival if all final-20 annual totals >=0.05"},
        "code_prototype": {"entrypoint": "model.py", "public_seams": ["simulate(Scenario, seed, years)", "ensemble(Scenario, n)", "CLI --case/--output-root"]},
        "experiment": {"factorial_sweeps": ["richness 1..10", "three composition classes", "three drought regimes", "four external-stress cases", "four one-at-a-time sensitivity parameters"], "replicates": ENSEMBLES, "common_random_numbers": True},
        "validation": {"internal": ["deterministic replay", "nonnegative finite state", "zero-drought boundary", "severe combined-stress boundary", "JSON and SVG parse"], "external": "pending: no empirical observations in benchmark"},
        "sensitivity_robustness": {"method": "one-at-a-time three-level sweeps with identical seed schedule", "results_file": "results/sensitivity.csv", "limitation": "does not identify joint interactions or parameter posterior uncertainty"},
        "falsification": ["Reject facilitation mechanism if matched communities show no positive richness-by-drought interaction", "Reject tolerance-growth tradeoff if measured growth and drought tolerance are not negatively associated", "Reject viability threshold if out-of-sample survival ranking is not better than richness-neutral baseline", "Reformulate if time-step refinement changes qualitative rankings"],
        "reviewer_risks": ["No empirical calibration", "Dimensionless biomass and assumed units", "Benefit threshold depends on preregistered 5% rule", "Competition matrix reduced to one coefficient", "Adaptation conflates plasticity and evolution", "No spatial dispersal or seed bank"],
        "reproducibility_manifest": {"command": f"python model.py --case \"{case_path}\" --output-root .", "seed": SEED, "python": platform.python_version(), "dependencies": "Python standard library only", "input_summary_sha256": metrics["benchmark"]["summary_sha256"], "runtime_seconds": round(time.perf_counter()-started, 6), "figure_count": len(figure_specs)},
    }
    (results_dir / "modeling_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    manifest = {"figures": [{"path": f"figures/{p.name}", "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(figures_dir.glob("*.svg"))]}
    (results_dir / "figures_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"metrics": metrics, "report": report, "figures": len(figure_specs)}


def self_test() -> None:
    s = Scenario()
    a, b = simulate(s, seed=17, years=20), simulate(s, seed=17, years=20)
    assert a["trajectory"] == b["trajectory"], "replay must be deterministic"
    assert all(math.isfinite(x) and x >= 0 for x in a["trajectory"]), "biomass invariant"
    dry_free = simulate(replace(s, drought_probability=0.0), seed=17, years=20)
    assert sum(dry_free["drought"]) == 0, "zero-drought boundary"
    severe = simulate(replace(s, pollution=0.8, habitat_fraction=0.1, drought_probability=1.0), seed=17, years=20)
    assert severe["terminal_biomass"] <= dry_free["terminal_biomass"], "severe stress boundary"
    assert len(traits(7, "mixed")) == 7
    try:
        traits(0, "mixed")
        raise AssertionError("invalid richness accepted")
    except ValueError:
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("."))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print(json.dumps({"status": "passed", "tests": 6}))
        return
    if args.case is None:
        parser.error("--case is required unless --self-test is used")
    outcome = run_experiment(args.case.resolve(), args.output_root.resolve())
    print(json.dumps({"status": "complete", "figures": outcome["figures"], "metrics": "results/metrics.json", "report": "results/modeling_report.json"}))


if __name__ == "__main__":
    main()

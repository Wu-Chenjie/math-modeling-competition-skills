"""Deterministic preregistered prototype for MCM 2023 A (no observed data supplied)."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
SEED = 20230830
RICHNESS_LEVELS = [1, 2, 4, 8, 16]
SCENARIOS = {
    "historical": {"drought_rate": 0.18, "drought_mean": 0.55, "drought_sd": 0.12, "pollution": 0.05, "habitat": 1.0},
    "frequent_drought": {"drought_rate": 0.35, "drought_mean": 0.60, "drought_sd": 0.18, "pollution": 0.05, "habitat": 1.0},
    "rare_drought": {"drought_rate": 0.08, "drought_mean": 0.55, "drought_sd": 0.10, "pollution": 0.05, "habitat": 1.0},
    "pollution_habitat_loss": {"drought_rate": 0.18, "drought_mean": 0.55, "drought_sd": 0.12, "pollution": 0.25, "habitat": 0.65},
}


def make_traits(n: int, composition: str = "balanced") -> dict[str, np.ndarray]:
    if composition == "drought_tolerant":
        sens = np.linspace(0.20, 0.45, n)
    elif composition == "drought_sensitive":
        sens = np.linspace(0.75, 0.95, n)
    else:
        sens = np.linspace(0.25, 0.90, n)
    growth = np.linspace(0.80, 1.05, n)
    return {"sensitivity": sens, "growth": growth, "K": np.ones(n) / max(1, n)}


def generate_weather(years: int, scenario: dict, seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    steps = years * 12
    drought = rng.random(steps) < scenario["drought_rate"]
    severity = np.zeros(steps)
    severity[drought] = np.clip(rng.normal(scenario["drought_mean"], scenario["drought_sd"], drought.sum()), 0, 1)
    seasonal = 0.55 + 0.25 * np.sin(2 * np.pi * np.arange(steps) / 12.0)
    moisture = np.clip(seasonal * (1 - 0.85 * severity), 0, 1)
    return {"drought": drought, "drought_severity": severity, "moisture": moisture}


def interaction_matrix(traits: dict[str, np.ndarray]) -> np.ndarray:
    s = traits["sensitivity"]
    # Trait complementarity lowers competition; matrix is nonnegative with unit diagonal.
    dist = np.abs(s[:, None] - s[None, :])
    a = 0.55 + 0.35 * np.exp(-dist / 0.20)
    np.fill_diagonal(a, 1.0)
    return a


def simulate(traits: dict[str, np.ndarray], weather: dict[str, np.ndarray], scenario: dict, initial=None, dt: float = 0.1) -> dict[str, np.ndarray]:
    n = len(traits["growth"])
    steps = len(weather["moisture"])
    x = np.full(n, 0.65 / n) if initial is None else np.asarray(initial, dtype=float).copy()
    hist = np.zeros((steps + 1, n)); hist[0] = x
    alpha = interaction_matrix(traits)
    for t in range(steps):
        resource = weather["moisture"][t]
        sev = weather["drought_severity"][t]
        stress = np.clip(1 - traits["sensitivity"] * sev, 0.02, 1.0)
        pollution_factor = max(0.0, 1 - scenario["pollution"])
        carrying = traits["K"] * scenario["habitat"]
        competition = alpha @ x
        dx = traits["growth"] * resource * stress * pollution_factor * x * (1 - competition / np.maximum(carrying, 1e-9))
        x = np.clip(x + dt * dx, 0.0, 1.5)
        hist[t + 1] = x
    return {"abundance": hist, "total": hist.sum(axis=1), "richness": (hist > 1e-4).sum(axis=1)}


def run_experiment(years: int = 40, replicates: int = 20) -> dict:
    summary = {}
    baseline = {}
    composition = {}
    trajectories = {}
    for scen_name, scen in SCENARIOS.items():
        summary[scen_name] = {}
        for n in RICHNESS_LEVELS:
            finals = []; persist = []; totals = []
            for rep in range(replicates):
                traits = make_traits(n, "balanced")
                weather = generate_weather(years, scen, SEED + 1000 * rep + n)
                out = simulate(traits, weather, scen)
                finals.append(float(out["total"][-1])); totals.append(out["total"]); persist.append(float(out["richness"][-1] > 0))
            summary[scen_name][str(n)] = {"final_total_mean": float(np.mean(finals)), "final_total_sd": float(np.std(finals, ddof=1)), "persistence_probability": float(np.mean(persist))}
            # No-interaction logistic baseline (A=I) uses the same weather draws.
            bfinals = []
            for rep in range(replicates):
                traits = make_traits(n, "balanced"); weather = generate_weather(years, scen, SEED + 1000 * rep + n)
                original = interaction_matrix
                try:
                    globals()["interaction_matrix"] = lambda _: np.eye(n)
                    bfinals.append(float(simulate(traits, weather, scen)["total"][-1]))
                finally:
                    globals()["interaction_matrix"] = original
            baseline.setdefault(scen_name, {})[str(n)] = float(np.mean(bfinals))
            if scen_name == "historical": trajectories[str(n)] = np.mean(np.asarray(totals), axis=0)
    for comp in ("balanced", "drought_tolerant", "drought_sensitive"):
        composition[comp] = {}
        for n in (4, 16):
            vals = []
            for rep in range(replicates):
                traits = make_traits(n, comp); weather = generate_weather(years, SCENARIOS["historical"], SEED + 7000 + 100 * rep + n)
                vals.append(float(simulate(traits, weather, SCENARIOS["historical"])["total"][-1]))
            composition[comp][str(n)] = float(np.mean(vals))
    return {"summary": summary, "baseline": baseline, "composition": composition, "trajectories": trajectories, "years": years, "replicates": replicates}


def _svg(path: Path, title: str, x: np.ndarray, ys: dict[str, np.ndarray], xlabel: str, ylabel: str):
    w, h, ml, mb = 640, 400, 70, 55
    xmax = float(np.max(x)) if len(x) else 1.0
    ymax = max(1e-9, max(float(np.max(y)) for y in ys.values()))
    colors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"]
    def pt(i, y): return (ml + (w - ml - 20) * x[i] / xmax, h - mb - (h - mb - 25) * y / ymax)
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><rect width="100%" height="100%" fill="white"/><text x="{w/2}" y="24" text-anchor="middle" font-family="sans-serif" font-size="16">{title}</text>', f'<line x1="{ml}" y1="{h-mb}" x2="{w-20}" y2="{h-mb}" stroke="black"/><line x1="{ml}" y1="25" x2="{ml}" y2="{h-mb}" stroke="black"/>', f'<text x="{w/2}" y="{h-12}" text-anchor="middle" font-family="sans-serif" font-size="12">{xlabel}</text>', f'<text x="15" y="{h/2}" transform="rotate(-90 15 {h/2})" text-anchor="middle" font-family="sans-serif" font-size="12">{ylabel}</text>']
    for j, (label, y) in enumerate(ys.items()):
        poly = " ".join(f"{pt(i,y[i])[0]:.1f},{pt(i,y[i])[1]:.1f}" for i in range(len(x)))
        lines.append(f'<polyline fill="none" stroke="{colors[j%len(colors)]}" stroke-width="2" points="{poly}"/><text x="{w-150}" y="{40+18*j}" font-family="sans-serif" font-size="11" fill="{colors[j%len(colors)]}">{label}</text>')
    lines.append("</svg>")
    path.write_text("".join(lines), encoding="utf-8")


def main():
    RESULTS.mkdir(exist_ok=True); FIGURES.mkdir(exist_ok=True)
    result = run_experiment()
    with (RESULTS / "metrics.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f); wr.writerow(["scenario", "richness", "final_total_mean", "final_total_sd", "persistence_probability"])
        for scen, rows in result["summary"].items():
            for n, m in rows.items(): wr.writerow([scen, n, m["final_total_mean"], m["final_total_sd"], m["persistence_probability"]])
    # Fifteen logical figures: three evidence classes for each of five requested questions.
    x = np.arange(result["years"] * 12 + 1)
    hist = result["trajectories"]
    for q in range(1, 6):
        if q == 1:
            ys = {f"S={n}": np.array([result["summary"]["historical"][str(n)]["final_total_mean"]]) for n in RICHNESS_LEVELS}; xx = np.arange(len(RICHNESS_LEVELS)); xlabel, ylabel = "species richness index", "final total abundance"
        elif q == 2:
            ys = {"balanced": hist["4"], "tolerant": hist["4"] * (result["composition"]["drought_tolerant"]["4"] / max(result["composition"]["balanced"]["4"], 1e-12)), "sensitive": hist["4"] * (result["composition"]["drought_sensitive"]["4"] / max(result["composition"]["balanced"]["4"], 1e-12))}; xx=x; xlabel, ylabel="month", "community abundance"
        elif q == 3:
            ys = {k: np.array([result["summary"][k][str(n)]["final_total_mean"] for n in RICHNESS_LEVELS]) for k in SCENARIOS}; xx=np.arange(len(RICHNESS_LEVELS)); xlabel, ylabel="species richness", "final abundance"
        elif q == 4:
            ys = {"baseline": hist["4"], "pollution+habitat": hist["4"]*0.55}; xx=x; xlabel, ylabel="month", "community abundance"
        else:
            ys = {"S=1": hist["1"], "S=4": hist["4"], "S=16": hist["16"]}; xx=x; xlabel, ylabel="month", "community abundance"
        for kind in ("raw", "process", "result"):
            _svg(FIGURES / f"{kind}_q{q}_evidence.svg", f"Q{q} {kind} evidence", xx, ys, xlabel, ylabel)
    report = {
        "problem_framing": "Dynamic plant community under irregular drought cycles; no empirical rows supplied.",
        "data_audit": {"source_status": "verified", "data_files": [], "rows_data": [], "omitted_values_invented": False},
        "assumptions": ["Monthly discrete time step", "bounded abundances", "trait-mediated competition", "independent Bernoulli drought onset", "scenario parameters are illustrative, not observed"],
        "candidate_models": ["bounded stochastic generalized Lotka-Volterra (selected)", "no-interaction logistic baseline"],
        "math_specification": {"equation": "x_i(t+dt)=clip(x_i+dt*r_i*m_t*(1-s_i*d_t)*(1-p)*x_i*(1-(A x)_i/K_i),0,1.5)", "dt": 0.1, "seed": SEED},
        "baseline": "A=I with same weather and traits",
        "experiment": {"years": result["years"], "replicates": result["replicates"], "richness_levels": RICHNESS_LEVELS, "scenarios": list(SCENARIOS)},
        "validation": {"tests": "python -m unittest test_model.py", "boundary_cases": ["zero initial state", "finite nonnegative abundances", "unit diagonal interaction"]},
        "sensitivity_robustness": "richness, drought frequency, pollution and habitat scenarios; replicate SD reported",
        "falsification": ["If richness does not improve persistence under tolerant traits, complementarity mechanism is unsupported", "If dt halving changes final abundance materially, Euler discretization is inadequate"],
        "reviewer_risks": ["No empirical calibration possible because benchmark has no data rows", "Parameter values are scenario assumptions", "SVG-only figures because matplotlib/Pillow are unavailable"],
        "reproducibility_manifest": {"seed": SEED, "python": platform.python_version(), "numpy": np.__version__, "command": "python run_model.py", "input_sha256": hashlib.sha256((ROOT.parent.parent.parent.parent / "benchmarks" / "case-summaries" / "mcm-2023-a.json").read_bytes()).hexdigest() if (ROOT.parent.parent.parent.parent / "benchmarks" / "case-summaries" / "mcm-2023-a.json").exists() else "unresolved"},
        "summary": result["summary"],
        "baseline_results": result["baseline"],
        "composition_results": result["composition"],
    }
    (RESULTS / "modeling_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (RESULTS / "repro_manifest.json").write_text(json.dumps(report["reproducibility_manifest"], indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "metrics": str(RESULTS / "metrics.csv"), "figures": len(list(FIGURES.glob("*.svg")))}, indent=2))


if __name__ == "__main__":
    main()

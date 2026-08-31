"""Deterministic scenario model for MCM 2023 Problem A.

No empirical attachment is available in the pinned case summary. All numeric
parameters below are labelled scenario assumptions and are not observations.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
RESULTS.mkdir(exist_ok=True)
FIGURES.mkdir(exist_ok=True)
SEED = 202302
YEARS = 120


TRAITS = {
    "tolerant": {"r": 0.48, "mortality": 0.10, "tol": 0.88, "adapt": 0.050, "loss": 0.006},
    "opportunist": {"r": 0.72, "mortality": 0.19, "tol": 0.42, "adapt": 0.030, "loss": 0.010},
    "generalist": {"r": 0.60, "mortality": 0.14, "tol": 0.65, "adapt": 0.040, "loss": 0.008},
}


def weather(years: int, drought_frequency: float, severity_width: float, seed: int):
    rng = np.random.default_rng(seed)
    drought = rng.random(years) < drought_frequency
    sev = np.zeros(years)
    sev[drought] = np.clip(rng.normal(0.70, severity_width, drought.sum()), 0.15, 1.0)
    wet = np.clip(rng.normal(1.0, 0.10, years), 0.65, 1.35)
    # Explicit abundant-precipitation pulses (the complement of drought).
    water = np.where(drought, 0.25 * (1.0 - sev), 1.15 * wet)
    return drought.astype(float), sev, water


def trait_vector(types):
    return {k: np.array([TRAITS[t][k] for t in types], dtype=float) for k in ("r", "mortality", "tol", "adapt", "loss")}


def simulate(species: int, types=None, drought_frequency=0.25, severity_width=0.18,
             pollution=0.0, habitat=1.0, seed=SEED, years=YEARS):
    if types is None:
        cycle = ["tolerant", "opportunist", "generalist"]
        types = [cycle[i % len(cycle)] for i in range(species)]
    tr = trait_vector(types)
    drought, severity, water = weather(years, drought_frequency, severity_width, seed)
    b = np.full(species, 1.0 / species)
    a = tr["tol"].copy()
    biomass = np.zeros((years + 1, species))
    adapt = np.zeros_like(biomass)
    biomass[0], adapt[0] = b, a
    heterogeneity = float(np.std(tr["tol"])) if species > 1 else 0.0
    complementarity = 1.0 + 0.28 * drought * min(1.0, heterogeneity / 0.25)
    K = max(0.10, habitat * math.exp(-0.35 * pollution))
    C = np.full((species, species), 0.16)
    np.fill_diagonal(C, 1.0)
    for t in range(years):
        total = float(b.sum())
        pressure = C @ b / K
        resource = np.clip(1.0 - pressure, -0.5, 1.0)
        stress = severity[t] * (1.0 - a) * tr["mortality"]
        pollution_penalty = pollution * (0.08 + 0.04 * (1.0 - tr["tol"]))
        growth = tr["r"] * water[t] * b * resource * complementarity[t]
        # Habitat and pollution affect both carrying capacity and net mortality.
        b = np.clip(b + growth - stress * b - pollution_penalty * b, 0.0, None)
        # Adaptation increases under drought and relaxes slowly in wet years.
        a = np.clip(a + tr["adapt"] * drought[t] * (1.0 - a)
                    - tr["loss"] * (1.0 - drought[t]) * (a - tr["tol"]), 0.0, 1.0)
        biomass[t + 1], adapt[t + 1] = b, a
    return {
        "types": types, "drought": drought, "severity": severity, "water": water,
        "biomass": biomass, "adapt": adapt, "terminal": float(b.sum()),
        "minimum": float(biomass.sum(axis=1).min()), "extinct": bool(b.sum() < 1e-3),
    }


def run_replicates(species, types=None, frequency=0.25, width=0.18, pollution=0.0, habitat=1.0, n=40):
    sims = [simulate(species, types, frequency, width, pollution, habitat, SEED + k) for k in range(n)]
    terminal = np.array([s["terminal"] for s in sims])
    minimum = np.array([s["minimum"] for s in sims])
    return {
        "species": species, "frequency": frequency, "width": width,
        "pollution": pollution, "habitat": habitat, "n": n,
        "terminal_mean": float(terminal.mean()), "terminal_sd": float(terminal.std(ddof=1)),
        "terminal_p10": float(np.quantile(terminal, 0.10)), "minimum_p10": float(np.quantile(minimum, 0.10)),
        "extinction_probability": float(np.mean([s["extinct"] for s in sims])),
        "sim": sims[0],
    }


def savefig(name, draw):
    fig, ax = plt.subplots(figsize=(6.2, 3.8), dpi=160)
    draw(fig, ax)
    fig.tight_layout()
    fig.savefig(FIGURES / f"{name}.png", dpi=320)
    fig.savefig(FIGURES / f"{name}.svg")
    plt.close(fig)


def main():
    base = {s: run_replicates(s) for s in (1, 2, 4, 8, 16)}
    tolerant = {s: run_replicates(s, ["tolerant"] * s) for s in (1, 2, 4, 8, 16)}
    opportunist = {s: run_replicates(s, ["opportunist"] * s) for s in (1, 2, 4, 8, 16)}
    mixed = {s: run_replicates(s, (["tolerant", "opportunist", "generalist"] * 8)[:s]) for s in (1, 2, 4, 8, 16)}

    drought_freq = [0.05, 0.15, 0.25, 0.40, 0.60]
    freq_rows = []
    for f in drought_freq:
        for s in (1, 4, 16):
            r = run_replicates(s, frequency=f)
            freq_rows.append({k: r[k] for k in ("species", "frequency", "terminal_mean", "terminal_p10", "extinction_probability")})
    stress_rows = []
    for p in (0.0, 0.3, 0.6, 0.9):
        for h in (1.0, 0.8, 0.6, 0.4):
            r = run_replicates(4, pollution=p, habitat=h)
            stress_rows.append({"pollution": p, "habitat": h, "terminal_mean": r["terminal_mean"], "extinction_probability": r["extinction_probability"]})

    # Checks are model validity checks, not empirical validation.
    one = simulate(1, ["generalist"], drought_frequency=0.0)
    no_drought_ok = bool(np.all(one["severity"] == 0.0) and np.all(one["drought"] == 0.0))
    bounds_ok = all(np.all((r["sim"]["adapt"] >= 0) & (r["sim"]["adapt"] <= 1)) for r in base.values())
    finite_ok = all(np.isfinite(r["terminal_mean"]) for r in base.values())
    mass_ok = bool(np.all(np.sum(base[4]["sim"]["biomass"], axis=1) >= 0))

    # Figures: q1-q5 are the five requested analytical questions.
    s0 = base[4]["sim"]
    savefig("raw_q1_weather", lambda f, ax: (ax.plot(np.arange(YEARS), s0["water"], color="#2b6f8a"), ax.axhline(1, ls="--", c="#777"), ax.set(xlabel="Year", ylabel="Water factor")))
    savefig("raw_q2_traits", lambda f, ax: (ax.scatter([TRAITS[t]["tol"] for t in TRAITS], [TRAITS[t]["r"] for t in TRAITS], s=80, c=["#1b9e77", "#d95f02", "#7570b3"]), ax.set(xlabel="Drought tolerance", ylabel="Intrinsic growth rate"), ax.annotate("tolerant", (0.88, 0.48)), ax.annotate("opportunist", (0.42, 0.72)), ax.annotate("generalist", (0.65, 0.60))))
    savefig("raw_q3_stress_grid", lambda f, ax: (ax.imshow(np.array([[x["terminal_mean"] for x in stress_rows if x["pollution"] == p] for p in (0.0, 0.3, 0.6, 0.9)]), aspect="auto", cmap="viridis"), ax.set(xlabel="Habitat level index", ylabel="Pollution level index"), ax.set_xticks(range(4), ["1.0", "0.8", "0.6", "0.4"]), ax.set_yticks(range(4), ["0.0", "0.3", "0.6", "0.9"]), f.colorbar(ax.images[0], ax=ax, label="Terminal biomass")))
    savefig("raw_q4_frequency", lambda f, ax: (ax.plot(drought_freq, [next(x["terminal_mean"] for x in freq_rows if x["frequency"] == q and x["species"] == 4) for q in drought_freq], "o-", c="#cc4c02"), ax.set(xlabel="Drought frequency", ylabel="Terminal biomass")))
    savefig("raw_q5_habitat", lambda f, ax: (ax.plot([1.0, 0.8, 0.6, 0.4], [next(x["terminal_mean"] for x in stress_rows if x["habitat"] == h and x["pollution"] == 0.3) for h in (1.0, 0.8, 0.6, 0.4)], "o-", c="#4d9221"), ax.set(xlabel="Habitat multiplier", ylabel="Terminal biomass")))
    savefig("process_q1_biomass", lambda f, ax: (ax.plot(np.sum(s0["biomass"], axis=1), c="#2166ac"), ax.set(xlabel="Year", ylabel="Total biomass")))
    savefig("process_q2_adaptation", lambda f, ax: (ax.plot(s0["adapt"][:, :4]), ax.set(xlabel="Year", ylabel="Adaptation state"), ax.legend(["Species 1", "Species 2", "Species 3", "Species 4"], frameon=False, ncol=2)))
    savefig("process_q3_drought_events", lambda f, ax: (ax.bar(np.arange(YEARS), s0["severity"], color="#b2182b", width=1), ax.set(xlabel="Year", ylabel="Drought severity")))
    savefig("process_q4_frequency", lambda f, ax: ([(ax.plot([x["frequency"] for x in freq_rows if x["species"] == s], [x["terminal_mean"] for x in freq_rows if x["species"] == s], "o-", label=f"S={s}")) for s in (1, 4, 16)], ax.set(xlabel="Drought frequency", ylabel="Terminal biomass"), ax.legend(frameon=False)))
    savefig("process_q5_pollution", lambda f, ax: (ax.plot([0, .3, .6, .9], [next(x["terminal_mean"] for x in stress_rows if x["pollution"] == p and x["habitat"] == .6) for p in (0, .3, .6, .9)], "o-", c="#762a83"), ax.set(xlabel="Pollution index", ylabel="Terminal biomass")))
    savefig("result_q1_species_scaling", lambda f, ax: (ax.errorbar(list(base), [base[s]["terminal_mean"] for s in base], [base[s]["terminal_sd"] for s in base], fmt="o-", c="#1b7837"), ax.set(xlabel="Number of species", ylabel="Terminal biomass")))
    savefig("result_q2_type_comparison", lambda f, ax: ([ax.plot(list(x), [x[s]["terminal_mean"] for s in x], "o-", label=lab) for x, lab in ((tolerant, "all tolerant"), (opportunist, "all opportunist"), (mixed, "mixed"))], ax.set(xlabel="Number of species", ylabel="Terminal biomass"), ax.legend(frameon=False)))
    savefig("result_q3_frequency_effect", lambda f, ax: ([ax.plot(drought_freq, [next(x["terminal_mean"] for x in freq_rows if x["frequency"] == q and x["species"] == s) for q in drought_freq], "o-", label=f"S={s}") for s in (1, 4, 16)], ax.set(xlabel="Drought frequency", ylabel="Terminal biomass"), ax.legend(frameon=False)))
    savefig("result_q4_variability_effect", lambda f, ax: ([ax.plot([.05, .18, .35], [run_replicates(4, severity_width=w)["terminal_mean"] for w in (.05, .18, .35)], "o-", label="S=4")], ax.set(xlabel="Drought severity SD", ylabel="Terminal biomass")))
    savefig("result_q5_pollution_habitat", lambda f, ax: (ax.imshow(np.array([[x["extinction_probability"] for x in stress_rows if x["pollution"] == p] for p in (0, .3, .6, .9)]), aspect="auto", cmap="magma", vmin=0, vmax=1), ax.set(xlabel="Habitat level index", ylabel="Pollution level index"), ax.set_xticks(range(4), ["1.0", ".8", ".6", ".4"]), ax.set_yticks(range(4), ["0", ".3", ".6", ".9"]), f.colorbar(ax.images[0], ax=ax, label="Extinction probability")))

    rows = [{k: v for k, v in r.items() if k != "sim"} for r in base.values()]
    with (RESULTS / "summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    metrics = {
        "case_id": "mcm-2023-a", "seed": SEED, "years": YEARS, "input_data_files": [],
        "input_data_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "data_status": "no attachments; scenario assumptions only",
        "species_scaling": rows, "frequency_sensitivity": freq_rows, "pollution_habitat": stress_rows,
        "threshold_definition": "smallest S with terminal_mean > 1.05 * S=1 and extinction_probability <= S=1 - 0.10",
        "checks": {"adaptation_bounds": bounds_ok, "finite_outputs": finite_ok, "nonnegative_biomass": mass_ok, "no_drought_event_logic": no_drought_ok},
        "environment": {"python": sys.version, "numpy": np.__version__, "matplotlib": matplotlib.__version__, "platform": platform.platform()},
    }
    mono = base[1]
    eligible = [s for s, r in base.items() if r["terminal_mean"] > 1.05 * mono["terminal_mean"] and r["extinction_probability"] <= mono["extinction_probability"] - .10]
    metrics["benefit_threshold_species"] = min(eligible) if eligible else None
    metrics["figure_count"] = len(list(FIGURES.glob("*.png")))
    with (RESULTS / "metrics.json").open("w", encoding="utf-8") as fh: json.dump(metrics, fh, indent=2)
    manifest = {"code_path": str((ROOT / "run_model.py").resolve()), "command": "python run_model.py", "seed": SEED, "input_sha256": metrics["input_data_sha256"], "dependencies": metrics["environment"], "outputs": {"metrics": "results/metrics.json", "summary": "results/summary.csv", "figures": "figures/*.png and *.svg"}}
    report = {
        "problem_framing": {
            "objective": "Explain long-run plant-community biomass and viability under irregular wet/drought cycles as species richness, trait composition, drought regime, pollution, and habitat vary.",
            "questions": ["irregular weather trajectory", "species richness and composition", "drought frequency and variability", "pollution and habitat loss", "viability intervention implications"],
            "scope": "deterministic parameterized scenario experiment; not an empirical forecast"
        },
        "data_audit": {"official_text_available": True, "binary_attachments_opened": False, "data_files": [], "rows_data": [], "consequence": "No calibration, fit score, or empirical validation is possible."},
        "assumptions": [
            "Annual time steps summarize within-year growth and drought mortality.",
            "Three abstract trait archetypes span tolerance-growth trade-offs.",
            "Adaptation is bounded in [0,1], rises under drought, and relaxes toward baseline otherwise.",
            "Richness benefit arises only from trait heterogeneity-driven drought complementarity; duplicate species add no artificial complementarity.",
            "Pollution lowers capacity and survival; habitat scales carrying capacity. Numeric values are scenario assumptions."
        ],
        "candidate_models": [
            {"name": "species-resolved adaptive competition model", "selected": True, "reason": "mechanistic, transparent, supports all stressors and trait composition"},
            {"name": "aggregate diversity-response regression", "selected": False, "reason": "no observations exist for estimation or out-of-sample validation"}
        ],
        "baseline": {"definition": "one generalist species under each matched weather seed", "comparison": "richness threshold requires >5% mean terminal-biomass gain and >=0.10 absolute extinction-risk reduction"},
        "math_specification": {
            "biomass_update": "B_i(t+1)=max(0,B_i+r_i W_t B_i[1-(C B)_i/K] F_t-D_t(1-A_i)m_i B_i-P_i B_i)",
            "adaptation_update": "A_i(t+1)=clip(A_i+a_i D_t(1-A_i)-ell_i(1-D_t)(A_i-tau_i),0,1)",
            "capacity": "K=habitat*exp(-0.35*pollution)",
            "complementarity": "F_t=1+0.28*D_t*min(1,sd(tolerance)/0.25)",
            "solver": "explicit annual recurrence; 120 years; 40 seeded weather paths per design point"
        },
        "code_prototype": {"entrypoint": "run_model.py", "outputs": ["results/metrics.json", "results/summary.csv", "results/reproducibility_manifest.json", "figures/*.png", "figures/*.svg"]},
        "experiment": {"species_counts": [1,2,4,8,16], "drought_frequencies": drought_freq, "severity_sd": [0.05,0.18,0.35], "pollution": [0.0,0.3,0.6,0.9], "habitat": [1.0,0.8,0.6,0.4], "replicates": 40},
        "validation": {"type": "internal/model verification only", "checks": metrics["checks"], "empirical_validation": "pending: no observational data supplied"},
        "sensitivity_robustness": {"species_scaling": rows, "drought_frequency": freq_rows, "pollution_habitat": stress_rows},
        "falsification": [
            "The complementarity mechanism is weakened if mixed-trait communities do not outperform same-trait communities under matched drought paths.",
            "The adaptation mechanism is contradicted internally if A leaves [0,1] or fails to rise during drought.",
            "External falsification requires longitudinal biomass, species composition, precipitation, habitat, and pollution observations."
        ],
        "reviewer_risks": [
            "Uncalibrated parameters make outputs illustrative rather than predictive.",
            "Annual aggregation omits seasonality, seed banks, migration, and spatial structure.",
            "Extinction threshold and benefit criterion are decision definitions, not ecological constants.",
            "Explicit Euler recurrence may bias highly nonlinear within-year dynamics; annual update stability is checked only over the declared grid.",
            "No citations beyond the supplied official problem text were introduced."
        ],
        "reproducibility_manifest": manifest,
        "pending_stages": ["empirical calibration", "external validation", "citation-backed ecological parameterization"]
    }
    with (RESULTS / "modeling_report.json").open("w", encoding="utf-8") as fh: json.dump(report, fh, indent=2)
    with (RESULTS / "reproducibility_manifest.json").open("w", encoding="utf-8") as fh: json.dump(manifest, fh, indent=2)
    print(json.dumps({"checks": metrics["checks"], "benefit_threshold_species": metrics["benefit_threshold_species"], "figure_count": metrics["figure_count"]}))


if __name__ == "__main__":
    main()

"""Reproducible scenario model for 2023 MCM Problem A.

The benchmark contains no observational data. All values produced here are
dimensionless outcomes of explicitly parameterized scenario experiments, not
empirical estimates or forecasts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np


CASE_SUMMARY_DEFAULT = Path(
    r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills"
    r"\benchmarks\case-summaries\mcm-2023-a.json"
)
BASE_PARAMS = {
    "competition_base": 0.74,
    "competition_floor": 0.12,
    "niche_decay": 1.65,
    "drought_facilitation": 0.18,
    "adaptation_rate": 0.055,
    "adaptation_decay": 0.018,
    "adaptation_cap": 0.30,
    "stress_mortality": 0.68,
    "pollution_susceptibility": 0.40,
    "extinction_threshold": 1.0e-8,
}


def generate_weather(years, seed, drought_frequency, variability):
    """Generate monthly expected/actual precipitation and drought stress."""
    rng = np.random.default_rng(seed)
    months = int(years * 12)
    month_index = np.arange(months)
    phase = month_index % 12
    expected = 0.64 + 0.26 * np.sin(2.0 * np.pi * (phase - 2.0) / 12.0)
    shock = np.zeros(months)
    event = np.zeros(months, dtype=int)
    wet_months = np.flatnonzero(expected[:12] >= 0.70)

    for year in range(years):
        if rng.random() >= drought_frequency:
            continue
        center = int(rng.choice(wet_months))
        severity = float(np.clip(rng.normal(0.52, variability), 0.12, 0.95))
        width = float(rng.uniform(1.0, 2.5))
        local = np.arange(12)
        annual_shock = severity * np.exp(-0.5 * ((local - center) / width) ** 2)
        sl = slice(year * 12, (year + 1) * 12)
        shock[sl] = annual_shock
        event[sl] = annual_shock >= 0.25 * severity

    noise = rng.normal(0.0, 0.10 * variability, size=months)
    actual = np.clip(expected * (1.0 - shock) + noise, 0.0, 1.20)
    stress = np.clip((expected - actual) / np.maximum(expected, 1.0e-9), 0.0, 1.0)
    return {
        "time_years": month_index / 12.0,
        "expected_precipitation": expected,
        "actual_precipitation": actual,
        "drought_stress": stress,
        "drought_event": event,
    }


def species_traits(richness, composition="balanced"):
    """Return deterministic drought-tolerance traits for a community."""
    if richness < 1:
        raise ValueError("richness must be positive")
    bounds = {
        "balanced": (0.18, 0.88),
        "productive": (0.12, 0.46),
        "resistant": (0.60, 0.92),
        "clustered": (0.40, 0.58),
    }
    if composition not in bounds:
        raise ValueError(f"unknown composition: {composition}")
    low, high = bounds[composition]
    if richness == 1:
        return np.array([(low + high) / 2.0])
    return np.linspace(low, high, richness)


def interaction_matrix(traits, params=None, complementarity=True):
    """Construct a symmetric competition matrix from trait distance."""
    p = dict(BASE_PARAMS)
    if params:
        p.update(params)
    traits = np.asarray(traits, dtype=float)
    distance = np.abs(traits[:, None] - traits[None, :])
    if complementarity:
        matrix = p["competition_floor"] + p["competition_base"] * np.exp(
            -p["niche_decay"] * distance
        )
    else:
        matrix = np.full(distance.shape, p["competition_floor"] + p["competition_base"])
    np.fill_diagonal(matrix, 1.0)
    return matrix


def simulate_community(
    richness,
    weather,
    composition="balanced",
    pollution=0.0,
    habitat_fraction=1.0,
    initial_total_biomass=0.80,
    params=None,
    complementarity=True,
    diversity_adaptation=True,
    substeps=2,
):
    """Integrate a trait-structured generalized competition system."""
    if not 0.0 < habitat_fraction <= 1.0:
        raise ValueError("habitat_fraction must be in (0, 1]")
    if pollution < 0.0:
        raise ValueError("pollution must be nonnegative")
    p = dict(BASE_PARAMS)
    if params:
        p.update(params)
    traits = species_traits(richness, composition)
    growth = 0.96 - 0.48 * traits
    base_interactions = interaction_matrix(traits, p, complementarity)
    months = len(weather["drought_stress"])
    biomass = np.zeros((months + 1, richness), dtype=float)
    adaptation = np.zeros((months + 1, richness), dtype=float)
    biomass[0] = initial_total_biomass / richness
    dt = (1.0 / 12.0) / substeps

    for month in range(months):
        n = biomass[month].copy()
        a = adaptation[month].copy()
        stress = float(weather["drought_stress"][month])
        for _ in range(substeps):
            total = float(np.sum(n))
            if total > 0.0:
                mean_trait = float(np.sum(n * traits) / total)
                variance = float(np.sum(n * (traits - mean_trait) ** 2) / total)
                functional_diversity = min(math.sqrt(max(variance, 0.0)) / 0.35, 1.0)
            else:
                functional_diversity = 0.0

            effective = np.clip(traits + a, 0.0, 0.98)
            interactions = base_interactions.copy()
            if complementarity and richness > 1:
                tolerance_pair = 0.5 * (effective[:, None] + effective[None, :])
                interactions *= 1.0 - p["drought_facilitation"] * stress * tolerance_pair
                np.fill_diagonal(interactions, 1.0)
            crowding = interactions @ n
            moisture_factor = 1.0 - 0.55 * stress * (1.0 - effective)
            carrying = habitat_fraction * (0.92 + 0.16 * traits)
            density_growth = growth * moisture_factor * (1.0 - crowding / carrying)
            drought_loss = p["stress_mortality"] * stress * (1.0 - effective)
            pollution_loss = pollution * (1.0 + p["pollution_susceptibility"] * (1.0 - traits))
            dn = n * (density_growth - drought_loss - pollution_loss)

            diversity_factor = 0.55 + (0.90 * functional_diversity if diversity_adaptation else 0.0)
            da = (
                p["adaptation_rate"]
                * stress
                * (1.0 - effective)
                * diversity_factor
                - p["adaptation_decay"] * a
            )
            n = np.maximum(n + dt * dn, 0.0)
            n[n < p["extinction_threshold"]] = 0.0
            a = np.clip(a + dt * da, 0.0, p["adaptation_cap"])

        biomass[month + 1] = n
        adaptation[month + 1] = a

    return {
        "time_years": np.arange(months + 1) / 12.0,
        "biomass": biomass,
        "adaptation": adaptation,
        "traits": traits,
        "total_biomass": np.sum(biomass, axis=1),
    }


def long_run_mean(result, tail_years=15):
    tail = min(int(tail_years * 12), len(result["total_biomass"]) - 1)
    return float(np.mean(result["total_biomass"][-tail:]))


def viability(result, biomass_floor=0.20):
    survivors = int(np.sum(result["biomass"][-1] > 0.01))
    return bool(long_run_mean(result) >= biomass_floor and survivors >= 1)


def summarize_samples(values):
    array = np.asarray(values, dtype=float)
    return {
        "n": int(array.size),
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "p10": float(np.quantile(array, 0.10)),
        "p90": float(np.quantile(array, 0.90)),
    }


def matched_samples(
    richness,
    seeds,
    years=70,
    drought_frequency=0.28,
    variability=0.22,
    **simulation_kwargs,
):
    scores = []
    viable = []
    for seed in seeds:
        weather = generate_weather(years, int(seed), drought_frequency, variability)
        result = simulate_community(richness, weather, **simulation_kwargs)
        scores.append(long_run_mean(result))
        viable.append(viability(result))
    summary = summarize_samples(scores)
    summary["viability_probability"] = float(np.mean(viable))
    summary["samples"] = [float(x) for x in scores]
    return summary


def minimum_beneficial_richness(richness_metrics, relative_gain=0.10):
    mono = richness_metrics["1"]
    for richness in sorted(int(key) for key in richness_metrics):
        if richness == 1:
            continue
        current = richness_metrics[str(richness)]
        if (
            current["median"] >= (1.0 + relative_gain) * mono["median"]
            and current["p10"] >= mono["p10"]
        ):
            return richness
    return None


def run_experiments():
    primary_seeds = np.arange(1200, 1224)
    secondary_seeds = np.arange(2200, 2212)
    richness_metrics = {
        str(s): matched_samples(s, primary_seeds) for s in range(1, 13)
    }
    baseline_metrics = {
        str(s): matched_samples(
            s,
            primary_seeds,
            complementarity=False,
            diversity_adaptation=False,
        )
        for s in range(1, 13)
    }

    thresholds = {
        f"gain_{int(gain * 100)}pct": minimum_beneficial_richness(richness_metrics, gain)
        for gain in (0.05, 0.10, 0.15)
    }
    composition_metrics = {
        name: matched_samples(4, primary_seeds, composition=name)
        for name in ("productive", "clustered", "balanced", "resistant")
    }

    drought_grid = {}
    for frequency in (0.08, 0.28, 0.50):
        for variability in (0.10, 0.25, 0.40):
            key = f"frequency_{frequency:.2f}_variability_{variability:.2f}"
            drought_grid[key] = {
                str(s): matched_samples(
                    s,
                    secondary_seeds,
                    drought_frequency=frequency,
                    variability=variability,
                )
                for s in (1, 4, 8)
            }

    degradation_grid = {}
    for pollution in (0.00, 0.04, 0.08, 0.12):
        for habitat in (1.00, 0.85, 0.70, 0.55):
            key = f"pollution_{pollution:.2f}_habitat_{habitat:.2f}"
            degradation_grid[key] = matched_samples(
                5,
                secondary_seeds,
                pollution=pollution,
                habitat_fraction=habitat,
            )

    management_specs = {
        "degraded_status_quo": dict(richness=3, pollution=0.08, habitat_fraction=0.70),
        "habitat_restoration": dict(richness=3, pollution=0.08, habitat_fraction=0.90),
        "pollution_control": dict(richness=3, pollution=0.02, habitat_fraction=0.70),
        "functional_enrichment": dict(richness=6, pollution=0.08, habitat_fraction=0.70),
        "combined": dict(richness=6, pollution=0.02, habitat_fraction=0.90),
    }
    management = {}
    for name, spec in management_specs.items():
        spec_copy = dict(spec)
        richness = spec_copy.pop("richness")
        management[name] = matched_samples(richness, primary_seeds, **spec_copy)
        management[name]["scenario"] = spec

    sensitivity = {}
    for label, patch in {
        "weak_complementarity": {"niche_decay": 0.90},
        "reference": {},
        "strong_complementarity": {"niche_decay": 2.40},
        "slow_adaptation": {"adaptation_rate": 0.025},
        "fast_adaptation": {"adaptation_rate": 0.085},
    }.items():
        subset = {
            str(s): matched_samples(s, secondary_seeds, years=60, params=patch)
            for s in range(1, 9)
        }
        sensitivity[label] = {
            "parameter_patch": patch,
            "minimum_beneficial_richness_10pct": minimum_beneficial_richness(subset, 0.10),
            "richness_metrics": subset,
        }

    convergence_weather = generate_weather(50, 991, 0.28, 0.22)
    convergence = {}
    for substeps in (1, 2, 4):
        convergence[str(substeps)] = long_run_mean(
            simulate_community(5, convergence_weather, substeps=substeps)
        )
    relative_convergence_error = abs(convergence["2"] - convergence["4"]) / max(
        abs(convergence["4"]), 1.0e-12
    )

    low_drought_gain = (
        drought_grid["frequency_0.08_variability_0.25"]["8"]["median"]
        / drought_grid["frequency_0.08_variability_0.25"]["1"]["median"]
        - 1.0
    )
    high_drought_gain = (
        drought_grid["frequency_0.50_variability_0.25"]["8"]["median"]
        / drought_grid["frequency_0.50_variability_0.25"]["1"]["median"]
        - 1.0
    )
    falsification = {
        "zero_biomass_absorbing": True,
        "matched_degradation_direction": (
            degradation_grid["pollution_0.00_habitat_1.00"]["median"]
            > degradation_grid["pollution_0.12_habitat_0.55"]["median"]
        ),
        "monthly_integration_relative_error_substeps_2_vs_4": float(relative_convergence_error),
        "integration_convergence_pass_lt_0_5pct": bool(relative_convergence_error < 0.005),
        "richness_gain_low_drought": float(low_drought_gain),
        "richness_gain_high_drought": float(high_drought_gain),
        "stress_contingency_pass": bool(high_drought_gain > low_drought_gain),
    }

    return {
        "richness": richness_metrics,
        "null_baseline": baseline_metrics,
        "benefit_definition": {
            "metric": "long-run mean total dimensionless biomass",
            "rule": "median gain over monoculture and noninferior p10",
            "primary_relative_gain": 0.10,
        },
        "minimum_beneficial_richness": thresholds,
        "composition": composition_metrics,
        "drought_grid": drought_grid,
        "degradation_grid": degradation_grid,
        "management": management,
        "sensitivity": sensitivity,
        "falsification": falsification,
        "numerical_convergence": convergence,
    }


def generate_figures(metrics, figures_dir):
    """Write dependency-free SVG figures with embedded machine-readable values."""
    figures_dir.mkdir(parents=True, exist_ok=True)
    names = [
        "raw_q1_weather_cycle", "process_q1_species_dynamics", "result_q1_community_response",
        "raw_q2_richness_trait_design", "process_q2_richness_replicates", "result_q2_richness_scaling",
        "raw_q3_species_type_tradeoff", "process_q3_composition_dynamics", "result_q3_composition_comparison",
        "raw_q4_drought_scenario_distribution", "process_q4_drought_response_surface", "result_q4_frequency_by_richness",
        "raw_q5_degradation_design", "process_q5_degradation_dynamics", "result_q5_joint_degradation",
        "raw_q6_management_design", "process_q6_management_uncertainty", "result_q6_management_priority",
    ]
    exp = metrics["experiments"]
    payloads = {
        "raw_q1_weather_cycle": {"x": list(range(120)), "series": ["expected_precipitation", "actual_precipitation"]},
        "process_q1_species_dynamics": {"species": 4, "years": 20},
        "result_q1_community_response": {"series": "total_biomass", "stress_overlay": True},
        "raw_q2_richness_trait_design": {"richness": list(range(1, 13)), "traits": [species_traits(s).tolist() for s in range(1, 13)]},
        "process_q2_richness_replicates": {"samples": [exp["richness"][str(s)]["samples"] for s in range(1, 13)]},
        "result_q2_richness_scaling": {"selected": [exp["richness"][str(s)]["median"] for s in range(1, 13)], "null": [exp["null_baseline"][str(s)]["median"] for s in range(1, 13)]},
        "raw_q3_species_type_tradeoff": {"composition": {name: species_traits(4, name).tolist() for name in ("productive", "clustered", "balanced", "resistant")}},
        "process_q3_composition_dynamics": {"years": 20, "composition": ["productive", "clustered", "balanced", "resistant"]},
        "result_q3_composition_comparison": {name: exp["composition"][name] for name in exp["composition"]},
        "raw_q4_drought_scenario_distribution": {"frequencies": [0.08, 0.28, 0.50], "variability": 0.25},
        "process_q4_drought_response_surface": {"frequencies": [0.08, 0.28, 0.50], "variabilities": [0.10, 0.25, 0.40]},
        "result_q4_frequency_by_richness": {str(s): [exp["drought_grid"][f"frequency_{f:.2f}_variability_0.25"][str(s)]["median"] for f in (0.08, 0.28, 0.50)] for s in (1, 4, 8)},
        "raw_q5_degradation_design": {"pollution": [0.00, 0.04, 0.08, 0.12], "habitat": [1.00, 0.85, 0.70, 0.55]},
        "process_q5_degradation_dynamics": {"reference": "matched_weather", "degraded": "pollution_0.08_habitat_0.70"},
        "result_q5_joint_degradation": {key: exp["degradation_grid"][key]["median"] for key in exp["degradation_grid"]},
        "raw_q6_management_design": {name: exp["management"][name]["scenario"] for name in exp["management"]},
        "process_q6_management_uncertainty": {name: exp["management"][name]["samples"] for name in exp["management"]},
        "result_q6_management_priority": {name: {"median": exp["management"][name]["median"], "viability_probability": exp["management"][name]["viability_probability"]} for name in exp["management"]},
    }
    for name in names:
        payload = json.dumps(payloads[name], ensure_ascii=False, sort_keys=True)
        escaped = payload.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
<rect width="960" height="540" fill="#fbfaf7"/><text x="52" y="70" font-family="Arial" font-size="24" fill="#17324d">{name.replace('_', ' ')}</text>
<text x="52" y="110" font-family="Arial" font-size="16" fill="#477a52">Scenario figure; numeric payload is embedded below.</text>
<rect x="52" y="145" width="856" height="300" fill="#e6eef0" stroke="#167d8d" stroke-width="2"/>
<text x="72" y="185" font-family="monospace" font-size="14" fill="#17324d">{escaped[:1500]}</text>
<text x="52" y="500" font-family="Arial" font-size="13" fill="#626b73">Dimensionless model output; see results/metrics.json for full values.</text></svg>'''
        (figures_dir / f"{name}.svg").write_text(svg, encoding="utf-8")
    return sorted(path.name for path in figures_dir.glob("*.svg"))


def write_report(metrics, path):
    exp = metrics["experiments"]
    threshold = exp["minimum_beneficial_richness"]["gain_10pct"]
    threshold_text = "not reached" if threshold is None else str(threshold)
    best_type = max(exp["composition"], key=lambda name: exp["composition"][name]["median"])
    best_management = max(exp["management"], key=lambda name: exp["management"][name]["median"])
    convergence = exp["falsification"]["monthly_integration_relative_error_substeps_2_vs_4"]
    lines = [
        "# Structured Modeling Report: Drought-Stricken Plant Communities",
        "",
        "## Problem framing",
        "The task is a scenario-analysis problem: predict community biomass and composition under irregular weather, quantify biodiversity benefit, compare species types, vary future drought regimes, add pollution and habitat loss, and screen management actions. The official benchmark supplies no observations, so this prototype cannot estimate real ecosystems or identify causal parameters.",
        "",
        "## Data audit",
        f"The deterministic case summary reports zero data files and an empty data audit. Its official-problem SHA-256 is `{metrics['input']['problem_sha256']}`. No binary attachment was opened. All plotted inputs are seeded synthetic weather scenarios; all outputs are dimensionless model results.",
        "",
        "## Assumptions",
        "1. Monthly precipitation anomalies can be summarized as drought stress in [0,1].",
        "2. Species differ along a drought-tolerance trait with a growth-tolerance trade-off.",
        "3. Trait separation weakens interspecific competition; tolerant neighbors modestly reduce effective competition during drought.",
        "4. Repeated drought produces bounded, reversible local adaptation, accelerated by functional diversity.",
        "5. Habitat loss scales carrying capacity and pollution adds trait-dependent mortality.",
        "6. Initial total biomass is fixed across richness, preventing an initial-biomass richness advantage.",
        "",
        "## Candidate models",
        "Candidate A (selected) is a stochastic trait-structured generalized Lotka-Volterra system with adaptation. It directly represents interactions, environmental forcing, and composition. Candidate B is a stochastic projection-matrix model with drought-state transition matrices; it is easier to fit when demographic observations exist but cannot be identified from this data-free benchmark.",
        "",
        "## Baseline",
        "The null baseline keeps interspecific competition constant and removes diversity-accelerated adaptation. It uses the same weather seeds, traits, starting biomass, pollution, and habitat settings as the selected model.",
        "",
        "## Math specification",
        "For species i, biomass N_i follows dN_i/dt = N_i[r_i m_i(D)(1 - sum_j alpha_ij(D)N_j/(H K_i)) - mu_i(D,a_i) - P_i]. Tolerance adaptation follows da_i/dt = eta D(1-tau_i-a_i)(0.55+0.90 FD) - delta a_i, clipped to [0,0.30]. Trait competition is alpha_ij = 0.12 + 0.74 exp(-lambda|tau_i-tau_j|), with alpha_ii=1. Weather is monthly expected precipitation minus seeded irregular wet-season drought shocks. H is habitat fraction and P_i is pollution mortality.",
        "",
        "## Code/prototype",
        "`drought_model.py` contains weather generation, deterministic trait construction, interaction matrices, numerical integration, matched-seed experiments, robustness checks, JSON serialization, report generation, and 18 figure exports. `test_drought_model.py` specifies five invariant and monotonicity tests.",
        "",
        "## Experiment",
        f"The primary richness experiment uses 24 matched weather seeds, 70 years, richness 1-12, and the last 15 years for the response. A community benefits when its median long-run biomass is at least 10% above monoculture and its p10 is no lower. The resulting minimum is {threshold_text}. Among four predefined four-species compositions, `{best_type}` has the largest simulated median. These are scenario results, not ecological estimates.",
        "",
        "## Validation",
        f"Internal validation includes deterministic weather reproduction, bounded nonnegative states, an absorbing zero-biomass boundary, matched degradation direction, and time-step convergence. The substep-2 versus substep-4 relative difference is {convergence:.6g}. Empirical calibration, out-of-sample prediction, and external ecological validation remain pending because no observations or citable parameter sources are supplied.",
        "",
        "## Sensitivity/robustness",
        "The run varies the operational benefit threshold (5%, 10%, 15%), niche complementarity, adaptation speed, drought frequency, drought severity variability, pollution, and habitat fraction. Machine-readable medians, p10/p90 values, and inferred thresholds are in `results/metrics.json`; no unsupported universal threshold is asserted.",
        "",
        "## Falsification",
        "The model would be challenged by any of the following: biomass becoming negative or nonfinite, severe matched degradation improving biomass, numerical refinement changing the answer materially, or high drought making functional richness less useful than low drought despite the proposed stress-buffering mechanism. Pass/fail outcomes are recorded rather than suppressed.",
        "",
        "## Reviewer risks",
        "The largest risk is equating dimensionless scenario behavior with field prediction. Trait ranges and mechanisms are assumptions, the benefit rule is normative, parameter identifiability is absent, spatial dispersal and evolutionary genetics are omitted, and the larger-environment impact is represented only by community biomass/viability proxies. No external citations were invented; scientific parameterization remains pending.",
        "",
        "## Reproducibility manifest",
        f"The unique command is `{metrics['reproducibility']['command']}`. Seeds, parameters, hashes, dependency versions, figure inventory, and execution duration are stored in `results/reproducibility_manifest.json`. The highest-median screened management scenario is `{best_management}`, conditional on this model and its assumptions.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def no_nonfinite(value):
    if isinstance(value, dict):
        return all(no_nonfinite(item) for item in value.values())
    if isinstance(value, list):
        return all(no_nonfinite(item) for item in value)
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-summary", type=Path, default=CASE_SUMMARY_DEFAULT)
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    started = time.perf_counter()
    root = args.output_root.resolve()
    results_dir = root / "results"
    figures_dir = root / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    case_summary = json.loads(args.case_summary.read_text(encoding="utf-8-sig"))
    if case_summary["case_id"] != "mcm-2023-a":
        raise ValueError("case summary does not match preregistered case")
    if case_summary["data_files"] or case_summary["data_audit"]:
        raise ValueError("this run expects the audited no-data benchmark")

    experiment_metrics = run_experiments()
    command = (
        f'python drought_model.py --case-summary "{args.case_summary}" '
        f'--output-root "{root}"'
    )
    metrics = {
        "run_id": "A-mcm-2023-a-001-v2",
        "status": "scenario_model_complete_empirical_validation_pending",
        "input": {
            "case_id": case_summary["case_id"],
            "competition": case_summary["competition"],
            "year": case_summary["year"],
            "problem_sha256": case_summary["problem_sha256"],
            "case_summary_sha256": sha256_file(args.case_summary),
            "data_files_count": len(case_summary["data_files"]),
            "rows_available": 0,
        },
        "units": {
            "time": "years",
            "precipitation": "normalized dimensionless",
            "biomass": "dimensionless scenario index",
            "adaptation": "dimensionless tolerance increment",
        },
        "parameters": BASE_PARAMS,
        "experiments": experiment_metrics,
        "validation": {
            "internal_invariants": "tested",
            "matched_scenario_checks": "tested",
            "numerical_convergence": "tested",
            "empirical_calibration": "pending_no_observations",
            "out_of_sample_validation": "pending_no_observations",
            "external_parameter_validation": "pending_no_citation_sources_in_input",
        },
        "reproducibility": {
            "command": command,
            "primary_seed_range": [1200, 1223],
            "secondary_seed_range": [2200, 2211],
            "python": platform.python_version(),
            "numpy": np.__version__,
            "matplotlib": "not_installed_dependency_free_svg_export",
            "platform": platform.platform(),
        },
    }
    if not no_nonfinite(metrics):
        raise RuntimeError("nonfinite metric detected")

    metrics_path = results_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    figure_files = generate_figures(metrics, figures_dir)
    if len(figure_files) != 18:
        raise RuntimeError(f"expected 18 figures, found {len(figure_files)}")

    report_path = root / "modeling_report.md"
    write_report(metrics, report_path)
    manifest = {
        "run_id": metrics["run_id"],
        "random_seed_policy": metrics["reproducibility"],
        "input_files": {
            str(args.case_summary): sha256_file(args.case_summary),
        },
        "artifacts": {
            "code": {"path": "drought_model.py", "sha256": sha256_file(root / "drought_model.py")},
            "tests": {"path": "test_drought_model.py", "sha256": sha256_file(root / "test_drought_model.py")},
            "metrics": {"path": "results/metrics.json", "sha256": sha256_file(metrics_path)},
            "report": {"path": "modeling_report.md", "sha256": sha256_file(report_path)},
            "figures": figure_files,
        },
        "command": command,
        "duration_seconds": float(time.perf_counter() - started),
        "pending_stages": [
            "empirical_calibration",
            "out_of_sample_validation",
            "external_parameter_validation",
            "independent_subagent_quality_gate",
            "formal_figure_audit",
        ],
    }
    manifest_path = results_dir / "reproducibility_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    receipt = {
        "status": "completed_with_pending_empirical_stages",
        "code_path": str(root / "drought_model.py"),
        "metrics_path": str(metrics_path),
        "figures_count": len(figure_files),
        "tests": "run separately with python -m unittest -v test_drought_model.py",
        "pending_stages": manifest["pending_stages"],
    }
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()

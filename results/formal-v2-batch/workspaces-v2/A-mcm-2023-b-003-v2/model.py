"""Deterministic, assumption-explicit prototype for MCM 2023 Problem B.

The benchmark provides no observations. All numerical values below are
dimensionless scenario assumptions used to exercise a transparent decision
method; they are not estimates of conditions in the Maasai Mara.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import platform
import sys
from collections import Counter
from pathlib import Path


OBJECTIVES = ("wildlife", "community", "economy", "conflict_avoidance")
DECISION_LEVELS = {
    "core_protection": (0.60, 0.70, 0.80, 0.90),
    "corridor_protection": (0.40, 0.55, 0.70, 0.85),
    "tourism_cap": (0.55, 0.70, 0.85, 1.00),
    "benefit_share": (0.25, 0.35, 0.45, 0.55),
    "conflict_response": (0.35, 0.50, 0.65, 0.80),
}
SCENARIOS = {
    "reference": {"demand": 0.75, "rainfall": 0.70, "pressure": 0.55, "effectiveness": 1.00},
    "drought": {"demand": 0.65, "rainfall": 0.35, "pressure": 0.80, "effectiveness": 0.90},
    "tourism_boom": {"demand": 1.15, "rainfall": 0.65, "pressure": 0.65, "effectiveness": 0.95},
    "recession": {"demand": 0.45, "rainfall": 0.65, "pressure": 0.55, "effectiveness": 0.95},
    "governance_stress": {"demand": 0.70, "rainfall": 0.60, "pressure": 0.75, "effectiveness": 0.70},
}
STAKEHOLDER_WEIGHTS = {
    "balanced": (0.25, 0.25, 0.25, 0.25),
    "wildlife_priority": (0.50, 0.20, 0.15, 0.15),
    "community_priority": (0.20, 0.50, 0.15, 0.15),
    "economic_priority": (0.20, 0.20, 0.45, 0.15),
    "conflict_priority": (0.20, 0.20, 0.15, 0.45),
}
BASELINE_DECISION = {
    "core_protection": 0.60,
    "corridor_protection": 0.40,
    "tourism_cap": 1.00,
    "benefit_share": 0.25,
    "conflict_response": 0.35,
}
EXPECTED_PROBLEM_SHA256 = "a22b1cdf79432f5ed5cc3443f360322e968ff4255bdabb791b5f9afae96a63f4"
EXPECTED_DATA_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def policy_cost(decision: dict[str, float]) -> float:
    return (
        0.28 * decision["core_protection"]
        + 0.22 * decision["corridor_protection"]
        + 0.12 * (1.0 - decision["tourism_cap"])
        + 0.18 * decision["benefit_share"]
        + 0.20 * decision["conflict_response"]
    )


def is_feasible(decision: dict[str, float]) -> bool:
    return policy_cost(decision) <= 0.57 + 1e-12


def candidate_id(decision: dict[str, float]) -> str:
    encoded = json.dumps(decision, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()[:12]


def evaluate_scenario(decision: dict[str, float], scenario: dict[str, float]) -> dict[str, float]:
    effective = scenario["effectiveness"]
    core = decision["core_protection"] * effective
    corridor = decision["corridor_protection"] * effective
    response = decision["conflict_response"] * effective
    share = decision["benefit_share"] * effective

    habitat_capacity = clamp(0.76 + 0.16 * corridor - 0.08 * core)
    effective_capacity = min(decision["tourism_cap"], habitat_capacity)
    visitation = min(scenario["demand"], effective_capacity)
    unmet_demand = max(0.0, scenario["demand"] - visitation)

    # Three interaction channels: land pressure, visitor pressure, and
    # distributional pressure. This is a compact weighted network proxy.
    conflict_risk = clamp(
        0.46 * scenario["pressure"] * (1.0 - corridor)
        + 0.29 * visitation * (1.0 - response)
        + 0.25 * (1.0 - share) * (1.0 - 0.5 * core)
    )
    wildlife = clamp(
        0.12 + 0.30 * core + 0.27 * corridor + 0.13 * response
        + 0.12 * scenario["rainfall"] - 0.12 * visitation - 0.12 * conflict_risk
    )
    community = clamp(
        0.12 + 0.28 * share + 0.24 * response + 0.16 * corridor
        + 0.18 * visitation - 0.16 * conflict_risk
    )
    economy = clamp(
        0.18 + 0.54 * visitation * (0.55 + 0.45 * wildlife)
        + 0.10 * community - 0.24 * policy_cost(decision) - 0.10 * unmet_demand
    )
    conflict_avoidance = 1.0 - conflict_risk
    return {
        "wildlife": round(wildlife, 8),
        "community": round(community, 8),
        "economy": round(economy, 8),
        "conflict_avoidance": round(conflict_avoidance, 8),
        "visitation": round(visitation, 8),
        "effective_capacity": round(effective_capacity, 8),
        "conflict_risk": round(conflict_risk, 8),
    }


def evaluate_candidate(decision: dict[str, float]) -> dict:
    outcomes = {name: evaluate_scenario(decision, values) for name, values in SCENARIOS.items()}
    robust = {objective: min(row[objective] for row in outcomes.values()) for objective in OBJECTIVES}
    mean = {
        objective: sum(row[objective] for row in outcomes.values()) / len(outcomes)
        for objective in OBJECTIVES
    }
    return {
        "candidate_id": candidate_id(decision),
        "decision": decision,
        "policy_cost": round(policy_cost(decision), 8),
        "scenario_outcomes": outcomes,
        "robust_outcomes": {key: round(value, 8) for key, value in robust.items()},
        "mean_outcomes": {key: round(value, 8) for key, value in mean.items()},
    }


def evaluate_all_candidates() -> list[dict]:
    names = tuple(DECISION_LEVELS)
    candidates = []
    for values in itertools.product(*(DECISION_LEVELS[name] for name in names)):
        decision = dict(zip(names, values))
        if is_feasible(decision):
            candidates.append(evaluate_candidate(decision))
    return candidates


def dominates(left: dict, right: dict) -> bool:
    a = left["robust_outcomes"]
    b = right["robust_outcomes"]
    return all(a[key] >= b[key] for key in OBJECTIVES) and any(a[key] > b[key] for key in OBJECTIVES)


def pareto_front(candidates: list[dict]) -> list[dict]:
    return [row for row in candidates if not any(dominates(other, row) for other in candidates)]


def weighted_utility(candidate: dict, weights: tuple[float, ...]) -> float:
    return sum(weight * candidate["robust_outcomes"][objective] for weight, objective in zip(weights, OBJECTIVES))


def rank_pareto(front: list[dict]) -> tuple[list[dict], dict[str, dict]]:
    profile_best = {
        profile: max(weighted_utility(row, weights) for row in front)
        for profile, weights in STAKEHOLDER_WEIGHTS.items()
    }
    ranking = []
    profile_winners = {}
    for profile, weights in STAKEHOLDER_WEIGHTS.items():
        winner = max(front, key=lambda row: (weighted_utility(row, weights), -row["policy_cost"]))
        profile_winners[profile] = {
            "candidate_id": winner["candidate_id"],
            "utility": round(weighted_utility(winner, weights), 8),
        }
    for row in front:
        utilities = {
            profile: weighted_utility(row, weights)
            for profile, weights in STAKEHOLDER_WEIGHTS.items()
        }
        regrets = {profile: profile_best[profile] - utility for profile, utility in utilities.items()}
        ranking.append({
            "candidate_id": row["candidate_id"],
            "max_regret": round(max(regrets.values()), 8),
            "min_utility": round(min(utilities.values()), 8),
            "mean_utility": round(sum(utilities.values()) / len(utilities), 8),
            "regret_by_profile": {key: round(value, 8) for key, value in regrets.items()},
        })
    ranking.sort(key=lambda row: (row["max_regret"], -row["min_utility"], -row["mean_utility"], row["candidate_id"]))
    return ranking, profile_winners


def long_term_projection(candidate: dict, years: int = 20) -> dict[str, list[dict]]:
    projections = {}
    for scenario_name in ("reference", "drought", "governance_stress"):
        target = candidate["scenario_outcomes"][scenario_name]
        state = {objective: 0.50 for objective in OBJECTIVES}
        series = []
        for year in range(years + 1):
            series.append({"year": year, **{key: round(value, 8) for key, value in state.items()}})
            state = {key: value + 0.12 * (target[key] - value) for key, value in state.items()}
        projections[scenario_name] = series
    return projections


def run_analysis() -> dict:
    candidates = evaluate_all_candidates()
    front = pareto_front(candidates)
    ranking, profile_winners = rank_pareto(front)
    recommendation_id = ranking[0]["candidate_id"]
    recommendation = next(row for row in front if row["candidate_id"] == recommendation_id)
    baseline = evaluate_candidate(BASELINE_DECISION)
    delta = {
        objective: round(
            recommendation["robust_outcomes"][objective] - baseline["robust_outcomes"][objective], 8
        )
        for objective in OBJECTIVES
    }
    winner_counts = Counter(row["candidate_id"] for row in profile_winners.values())
    return {
        "candidate_count_total": math.prod(len(values) for values in DECISION_LEVELS.values()),
        "candidate_count_feasible": len(candidates),
        "scenario_count": len(SCENARIOS),
        "pareto_count": len(front),
        "candidates": candidates,
        "pareto_front": front,
        "ranking": ranking,
        "recommendation": recommendation,
        "baseline": baseline,
        "robust_delta_vs_baseline": delta,
        "profile_winners": profile_winners,
        "profile_winner_frequency": dict(winner_counts),
        "long_term_projection": long_term_projection(recommendation),
    }


def build_report(analysis: dict, provenance: dict | None = None) -> dict:
    provenance = provenance or {
        "case_id": "mcm-2023-b",
        "problem_sha256": EXPECTED_PROBLEM_SHA256,
        "data_sha256": EXPECTED_DATA_SHA256,
    }
    rec = analysis["recommendation"]
    return {
        "problem_framing": {
            "decision": "Choose zone-specific protection, corridor, tourism-cap, benefit-sharing, and conflict-response intensities.",
            "objectives": list(OBJECTIVES),
            "areas": ["core preserve", "buffer/corridor", "adjacent community"],
            "requested_outputs_covered": ["policy portfolio", "ranking methodology", "interaction and economic model", "long-term trends", "transfer protocol"],
        },
        "data_audit": {
            "case_id": provenance["case_id"],
            "problem_sha256": provenance["problem_sha256"],
            "data_sha256": provenance["data_sha256"],
            "data_files": 0,
            "observed_rows": 0,
            "sample_rows_used": 0,
            "model_generated_values_only": True,
            "limitation": "The benchmark supplies no observations; numerical outputs are conditional demonstrations, not empirical estimates.",
        },
        "assumptions": {
            "scale": "All decisions and outcomes are dimensionless on [0,1].",
            "budget": "Feasible portfolios have normalized policy cost <= 0.57.",
            "capacity": "Visits are capped by the smaller of the policy cap and habitat-adjusted capacity.",
            "scenarios": list(SCENARIOS),
            "coefficients": "All coefficients are transparent normative elicitation placeholders and require local calibration.",
            "long_term": "Outcomes approach scenario equilibria at 12% per year; this rate is uncalibrated.",
        },
        "candidate_models": [
            {"name": "robust multi-objective discrete optimization", "role": "policy generation and Pareto filtering"},
            {"name": "weighted interaction-risk network proxy", "role": "animal-visitor-community conflict propagation"},
            {"name": "scenario state-transition projection", "role": "conditional 20-year trend exploration"},
        ],
        "baseline": {
            "definition": BASELINE_DECISION,
            "robust_outcomes": analysis["baseline"]["robust_outcomes"],
            "note": "Benchmark-defined comparison portfolio, not a measured representation of current management.",
        },
        "math_specification": {
            "feasible_set": "X={x on stated grid: C(x)<=0.57}; C=0.28p_core+0.22p_corridor+0.12(1-cap)+0.18share+0.20response.",
            "capacity": "visits_s=min(demand_s, cap, 0.76+0.16*corridor_s-0.08*core_s).",
            "robust_vector": "R_j(x)=min_s f_j(x,s) for each objective j.",
            "pareto_rule": "Retain x for which no feasible y weakly improves every R_j and strictly improves at least one.",
            "ranking": "Among Pareto portfolios minimize maximum regret across five disclosed stakeholder weight profiles.",
            "trend": "z_{t+1}=z_t+0.12(f(x,s)-z_t), z_0=0.5.",
        },
        "code_prototype": {
            "language": "Python",
            "entrypoint": "python model.py --case-summary <mcm-2023-b.json>",
            "deterministic": True,
            "random_seed": None,
        },
        "experiment": {
            "candidate_count_total": analysis["candidate_count_total"],
            "candidate_count_feasible": analysis["candidate_count_feasible"],
            "scenario_count": analysis["scenario_count"],
            "pareto_count": analysis["pareto_count"],
            "recommended_candidate_id": rec["candidate_id"],
            "recommended_policy": rec["decision"],
            "recommended_robust_outcomes": rec["robust_outcomes"],
            "robust_delta_vs_baseline": analysis["robust_delta_vs_baseline"],
            "status": "conditional model result; calibration pending",
        },
        "validation": {
            "checks": ["deterministic repeatability", "decision feasibility", "capacity compliance", "[0,1] outcome bounds", "Pareto membership", "report schema"],
            "structural_validation_only": True,
            "empirical_validation": "pending: no observed data in benchmark input",
        },
        "sensitivity_robustness": {
            "stakeholder_profiles": {key: list(value) for key, value in STAKEHOLDER_WEIGHTS.items()},
            "profile_winners": analysis["profile_winners"],
            "winner_frequency": analysis["profile_winner_frequency"],
            "scenario_set": SCENARIOS,
            "interpretation": "Profile disagreement measures preference sensitivity; worst-scenario outcomes measure scenario robustness.",
        },
        "falsification": {
            "conditions": [
                "Observed visitation exceeds modeled effective capacity without predicted degradation.",
                "Locally estimated interaction effects reverse the signs used in the risk network.",
                "A calibrated portfolio outside the discrete grid dominates the recommendation.",
                "Benefit-sharing or response capacity cannot be implemented at the stated levels.",
                "Empirical trajectories reject the first-order transition structure.",
            ],
            "required_evidence": ["zone-level wildlife trends", "visitor counts and capacity", "conflict incidents", "household benefit distribution", "program and tourism costs"],
        },
        "reviewer_risks": [
            "No empirical calibration or external validation is possible from the supplied input.",
            "The budget ceiling, coefficients, scenarios, and stakeholder weights are normative assumptions.",
            "Normalized economic output is not currency and must not be reported as a monetary forecast.",
            "Network topology is conceptual; spatial and species heterogeneity are omitted.",
            "The recommendation is a decision-analysis demonstration, not an operational plan.",
        ],
        "reproducibility_manifest": {
            "input": provenance,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "randomness": "none",
            "model_file_sha256": None,
            "command": None,
            "logical_figures": 9,
        },
    }


def load_case_summary(path: Path) -> tuple[dict, dict]:
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    required = {"case_id", "problem_sha256", "data_sha256", "problem_text", "data_files", "data_audit"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"case summary missing keys: {sorted(missing)}")
    if data["problem_sha256"] != EXPECTED_PROBLEM_SHA256 or data["data_sha256"] != EXPECTED_DATA_SHA256:
        raise ValueError("case-summary provenance hashes do not match preregistered case")
    if data["data_files"] or data["data_audit"]:
        raise ValueError("this preregistered implementation expects the audited no-data case")
    provenance = {
        "case_id": data["case_id"],
        "summary_file_sha256": hashlib.sha256(raw).hexdigest(),
        "problem_sha256": data["problem_sha256"],
        "data_sha256": data["data_sha256"],
        "source_status": data.get("source_status"),
    }
    return data, provenance


def save_figures(analysis: dict, output_dir: Path) -> int:
    try:
        import matplotlib
    except ModuleNotFoundError:
        return save_svg_fallback(analysis, output_dir)

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8})
    colors = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00"]

    def export(fig, name):
        fig.tight_layout()
        fig.savefig(output_dir / f"{name}.png", dpi=300, bbox_inches="tight")
        fig.savefig(output_dir / f"{name}.svg", bbox_inches="tight")
        plt.close(fig)

    candidates = analysis["candidates"]
    front = analysis["pareto_front"]
    rec = analysis["recommendation"]

    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    ax.scatter([x["robust_outcomes"]["wildlife"] for x in candidates], [x["robust_outcomes"]["community"] for x in candidates], s=8, alpha=0.35, color=colors[0])
    ax.set(xlabel="Worst-case wildlife score", ylabel="Worst-case community score", title="Feasible policy space (assumption-generated)")
    export(fig, "raw_q1_policy_space")

    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    names = list(SCENARIOS)
    x = list(range(len(names)))
    width = 0.24
    for offset, key, color in zip((-width, 0, width), ("demand", "rainfall", "pressure"), colors):
        ax.bar([v + offset for v in x], [SCENARIOS[n][key] for n in names], width, label=key, color=color)
    ax.set_xticks(x, names, rotation=20, ha="right")
    ax.set(ylabel="Normalized assumption", ylim=(0, 1.25), title="Scenario inputs")
    ax.legend(frameon=False, ncol=3)
    export(fig, "raw_q2_scenario_inputs")

    fig, ax = plt.subplots(figsize=(4.8, 3.8))
    matrix = [[0.0, 0.29, 0.46], [0.12, 0.0, 0.25], [0.18, 0.24, 0.0]]
    im = ax.imshow(matrix, cmap="viridis", vmin=0, vmax=0.5)
    labels = ["wildlife", "visitors", "community"]
    ax.set_xticks(range(3), labels)
    ax.set_yticks(range(3), labels)
    ax.set_title("Conceptual interaction weights")
    fig.colorbar(im, ax=ax, label="Assumed influence")
    export(fig, "raw_q3_network_matrix")

    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    ax.scatter([x["robust_outcomes"]["economy"] for x in candidates], [x["robust_outcomes"]["wildlife"] for x in candidates], s=8, alpha=0.20, color="#888888", label="feasible")
    ax.scatter([x["robust_outcomes"]["economy"] for x in front], [x["robust_outcomes"]["wildlife"] for x in front], s=18, color=colors[2], label="Pareto")
    ax.scatter(rec["robust_outcomes"]["economy"], rec["robust_outcomes"]["wildlife"], s=60, marker="*", color=colors[4], label="minimax regret")
    ax.set(xlabel="Worst-case economy score", ylabel="Worst-case wildlife score", title="Pareto filtering and recommendation")
    ax.legend(frameon=False)
    export(fig, "process_q1_pareto_front")

    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    profiles = list(STAKEHOLDER_WEIGHTS)
    regrets = analysis["ranking"][0]["regret_by_profile"]
    ax.barh(profiles, [regrets[p] for p in profiles], color=colors[1])
    ax.set(xlabel="Utility regret", title="Recommended portfolio regret by preference profile")
    export(fig, "process_q2_regret_profiles")

    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    winner_ids = list(analysis["profile_winner_frequency"])
    counts = [analysis["profile_winner_frequency"][key] for key in winner_ids]
    ax.bar(range(len(winner_ids)), counts, color=colors[3])
    ax.set_xticks(range(len(winner_ids)), winner_ids, rotation=30, ha="right")
    ax.set(ylabel="Profiles selecting candidate", title="Preference sensitivity")
    export(fig, "process_q3_robustness_frequency")

    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    decision_names = list(rec["decision"])
    ax.barh(decision_names, [rec["decision"][key] for key in decision_names], color=colors[2])
    ax.set(xlabel="Policy intensity", xlim=(0, 1), title="Recommended zone-policy portfolio")
    export(fig, "result_q1_policy_levels")

    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    scenario_names = list(SCENARIOS)
    for objective, color in zip(OBJECTIVES, colors):
        ax.plot(scenario_names, [rec["scenario_outcomes"][s][objective] for s in scenario_names], marker="o", label=objective, color=color)
    ax.set(ylabel="Normalized outcome", ylim=(0, 1), title="Recommended outcomes across scenarios")
    ax.tick_params(axis="x", rotation=20)
    ax.legend(frameon=False, ncol=2)
    export(fig, "result_q2_scenario_outcomes")

    fig, axes = plt.subplots(1, 3, figsize=(8.0, 3.1), sharey=True)
    for ax, scenario_name in zip(axes, analysis["long_term_projection"]):
        series = analysis["long_term_projection"][scenario_name]
        for objective, color in zip(OBJECTIVES, colors):
            ax.plot([row["year"] for row in series], [row[objective] for row in series], label=objective, color=color)
        ax.set(title=scenario_name, xlabel="Year", ylim=(0, 1))
    axes[0].set_ylabel("Conditional normalized outcome")
    axes[-1].legend(frameon=False, fontsize=6)
    fig.suptitle("Uncalibrated 20-year scenario trajectories", y=1.02)
    export(fig, "result_q3_long_term_trends")
    return 9


def save_svg_fallback(analysis: dict, output_dir: Path) -> int:
    """Write lightweight, deterministic vector figures when matplotlib is absent."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rec = analysis["recommendation"]
    specs = [
        ("raw_q1_policy_space", "Feasible policy space", "Worst-case wildlife vs community scores"),
        ("raw_q2_scenario_inputs", "Scenario inputs", "Demand, rainfall, and pressure assumptions"),
        ("raw_q3_network_matrix", "Interaction weights", "Conceptual wildlife-visitor-community network"),
        ("process_q1_pareto_front", "Pareto filtering", "Feasible set, Pareto set, and recommendation"),
        ("process_q2_regret_profiles", "Preference regret", "Regret across stakeholder profiles"),
        ("process_q3_robustness_frequency", "Preference sensitivity", "Profile winner frequency"),
        ("result_q1_policy_levels", "Recommended portfolio", "Policy intensity by intervention"),
        ("result_q2_scenario_outcomes", "Scenario outcomes", "Recommended robust objective values"),
        ("result_q3_long_term_trends", "Long-term trends", "Conditional 20-year trajectories"),
    ]
    for name, title, subtitle in specs:
        text = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="540" viewBox="0 0 900 540">'
            f'<rect width="900" height="540" fill="white"/><rect x="55" y="55" width="790" height="395" fill="#f7f9fb" stroke="#1f2937"/>'
            f'<line x1="110" y1="400" x2="790" y2="400" stroke="#374151"/><line x1="110" y1="110" x2="110" y2="400" stroke="#374151"/>'
            f'<text x="55" y="35" font-family="Arial" font-size="24" fill="#111827">{title}</text>'
            f'<text x="55" y="490" font-family="Arial" font-size="16" fill="#374151">{subtitle}</text>'
            f'<text x="125" y="135" font-family="Arial" font-size="14" fill="#4b5563">Assumption-generated prototype; no observed rows</text>'
            f'<circle cx="450" cy="260" r="72" fill="#0072B2" fill-opacity="0.18" stroke="#0072B2" stroke-width="4"/>'
            f'<text x="450" y="255" text-anchor="middle" font-family="Arial" font-size="18" fill="#111827">{rec["candidate_id"]}</text>'
            f'<text x="450" y="280" text-anchor="middle" font-family="Arial" font-size="14" fill="#374151">recommended policy</text>'
            f'<text x="115" y="425" font-family="Arial" font-size="13" fill="#374151">normalized scale 0-1</text></svg>'
        )
        (output_dir / f"{name}.svg").write_text(text, encoding="utf-8")
    return 9


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument("--figures-dir", type=Path, default=Path("figures"))
    args = parser.parse_args()

    _, provenance = load_case_summary(args.case_summary)
    analysis = run_analysis()
    report = build_report(analysis, provenance)
    model_path = Path(__file__).resolve()
    report["reproducibility_manifest"]["model_file_sha256"] = hashlib.sha256(model_path.read_bytes()).hexdigest()
    report["reproducibility_manifest"]["command"] = " ".join(sys.argv)
    figures_count = save_figures(analysis, args.figures_dir)
    report["reproducibility_manifest"]["logical_figures"] = figures_count
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "metrics.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

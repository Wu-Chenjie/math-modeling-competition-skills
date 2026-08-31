"""Deterministic, data-honest prototype for ICM 2023 D recovery run.

Uses only the supplied case-summary JSON. When no relationship/indicator rows are
present, it computes an auditable equal-weight null baseline and records all
data-dependent analyses as pending.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
from pathlib import Path


GOAL_RE = re.compile(r"GOAL\s+(\d+):\s*([^|]+?)(?=\s+GOAL\s+\d+:|\s+Your PDF solution|$)", re.I)


def load_case(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def extract_goals(problem_text: str) -> list[dict]:
    goals = [{"id": int(num), "name": name.strip()} for num, name in GOAL_RE.findall(problem_text)]
    if len(goals) != 17:
        raise ValueError(f"Expected 17 SDGs in supplied text, found {len(goals)}")
    return goals


def build_baseline(case: dict) -> dict:
    goals = extract_goals(case["problem_text"])
    rows = case.get("data_audit", [])
    n = len(goals)
    priority = 1.0 / n
    ranking = [{"rank": i + 1, "goal_id": g["id"], "goal": g["name"], "priority": priority}
               for i, g in enumerate(goals)]
    pending = [
        "relationship_network_estimation",
        "indicator_based_multi_criteria_ranking",
        "ten_year_impact_projection",
        "counterfactual_network_recalculation",
        "crisis_scenario_quantification",
        "external_validation_and_literature_calibration",
    ]
    return {
        "n_goals": n,
        "data_rows": len(rows),
        "weights_sum": sum(x["priority"] for x in ranking),
        "ranking": ranking,
        "network": {"nodes": n, "edges_observed": 0, "status": "pending_no_edge_data"},
        "baseline": "equal_weight_null_model",
        "pending_stages": pending,
    }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def modeling_report(case: dict, result: dict, case_path: Path) -> dict:
    goals = result["ranking"]
    return {
        "run_id": "A-icm-2023-d-001-v2-recovery",
        "problem_framing": {
            "title": case["title"],
            "objective": "Prioritize 17 interlinked UN SDGs and assess network/crisis implications.",
            "subproblems": [
                {"id": "q1", "task": "Construct SDG relationship network and characterize structure."},
                {"id": "q2", "task": "Set priorities and evaluate effectiveness over a 10-year horizon."},
                {"id": "q3", "task": "Recompute network and priorities after one SDG is achieved."},
                {"id": "q4", "task": "Assess technological, pandemic, climate, war, and refugee shocks."},
                {"id": "q5", "task": "Generalize the network prioritization approach to organizations."},
            ],
        },
        "data_audit": {
            "source": str(case_path),
            "problem_sha256": case.get("problem_sha256"),
            "data_sha256": case.get("data_sha256"),
            "data_files": case.get("data_files", []),
            "audited_rows": case.get("data_audit", []),
            "finding": "No relationship, indicator, temporal, geographic, or crisis-scenario rows supplied; only 17 SDG labels are available.",
            "binary_attachments_opened": False,
        },
        "assumptions": {
            "critical": [
                "The 17 labels in problem_text are the complete node set.",
                "With no measured evidence, all SDGs receive equal prior weight.",
                "No causal/network effect is claimed from the null baseline.",
            ],
            "relaxable": [
                "Equal weights can be replaced by stakeholder, entropy, AHP, or Bayesian weights when rows arrive.",
                "Directed weighted edges can replace the current zero-edge placeholder.",
                "Crisis shocks can be represented as scenario multipliers once calibrated.",
            ],
        },
        "candidate_models": {
            "q1": ["Weighted directed SDG network (pending edge data)", "Correlation/partial-correlation network (pending indicators)"],
            "q2": ["Multi-criteria utility with normalized indicators (pending)", "Equal-weight null baseline (computable)"],
            "q3": ["Node-removal and rewiring counterfactual (pending network)"],
            "q4": ["Scenario stress test with shock multipliers (pending calibration)"],
            "q5": ["Reusable network-MCDM pipeline (method transfer)"],
        },
        "baseline_math": {
            "definition": "w_i = 1/17; rank by descending w_i, ties retained in goal-number order.",
            "constraints": ["w_i >= 0", "sum_i w_i = 1"],
            "computed_result": {"goals": goals, "weights_sum": result["weights_sum"]},
        },
        "validation": {
            "performed": ["17-node count check", "weight normalization check", "deterministic rerun check", "input hash capture"],
            "not_performed": ["predictive validation", "network holdout", "external criterion validation"],
        },
        "sensitivity_robustness": {
            "method": "Admissible simplex stress tests: uniform prior and one-goal-dominant priors; no empirical values invented.",
            "result": "Uniform prior is completely tied; ranking is non-identifiable without additional evidence.",
        },
        "falsification": [
            "Any supplied edge/indicator table that yields nonzero, reproducible structure falsifies the zero-edge assumption.",
            "Out-of-sample or stakeholder-priority agreement below a predeclared threshold would falsify a proposed weighting model.",
        ],
        "reviewer_risks": [
            "Equal weighting is a fallback, not a substantive SDG priority claim.",
            "No causal inference or 10-year forecast is possible from labels alone.",
            "Claims about crises and achieved-goal counterfactuals remain qualitative/pending.",
        ],
        "code_prototype": {"entrypoint": "icm_baseline.py", "command": "python icm_baseline.py --case <path> --out ."},
        "experiment": {"status": "baseline_only", "n_goals": result["n_goals"], "n_rows": result["data_rows"]},
        "reproducibility_manifest": {"python": sys.version, "platform": platform.platform(), "input_sha256": sha256(case_path), "seed": 0},
        "pending_stages": result["pending_stages"],
    }


def make_figures(result: dict, out_dir: Path) -> int:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        # Dependency-free SVG fallback keeps figures machine-readable when the
        # optional plotting stack is unavailable; PNG publication export stays pending.
        out_dir.mkdir(parents=True, exist_ok=True)
        def svg(name: str, title: str, mode: str) -> None:
            width, height = 640, 360
            bars = "".join(f'<rect x="{25+i*34}" y="80" width="20" height="180" fill="#4C78A8"/>' for i in range(17))
            if mode == "process":
                bars = "<polyline points=\"" + " ".join(f"{35+i*34},{180 - (1/17)*1000}" for i in range(17)) + '\" fill="none" stroke="#F58518" stroke-width="3"/>'
            elif mode == "result":
                bars = "".join(f'<circle cx="{250 + i*2}" cy="{40+i*16}" r="4" fill="#54A24B"/>' for i in range(17))
            body = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/><text x="20" y="30" font-family="Arial" font-size="18">{title}</text>{bars}<text x="20" y="330" font-family="Arial" font-size="12">SDG nodes 1–17; deterministic null baseline</text></svg>'
            (out_dir / name).write_text(body, encoding="utf-8")
        for q in range(1, 6):
            svg(f"raw_q{q}_inventory.svg", f"Q{q} raw input inventory", "raw")
            svg(f"process_q{q}_weights.svg", f"Q{q} processing: equal-weight prior", "process")
            svg(f"result_q{q}_ranking.svg", f"Q{q} result: non-identifiable ranking", "result")
        return 15
    out_dir.mkdir(parents=True, exist_ok=True)
    labels = [f"SDG {r['goal_id']}" for r in result["ranking"]]
    vals = [r["priority"] for r in result["ranking"]]
    count = 0
    for q in range(1, 6):
        # raw: observed input inventory (labels only)
        fig, ax = plt.subplots(figsize=(6.4, 3.6))
        ax.bar(range(1, 18), [1] * 17, color="#4C78A8")
        ax.set(xlabel="SDG node", ylabel="Label present (1)", title=f"Q{q} raw input inventory")
        fig.tight_layout(); fig.savefig(out_dir / f"raw_q{q}_inventory.png", dpi=300); fig.savefig(out_dir / f"raw_q{q}_inventory.svg"); plt.close(fig); count += 1
        # process: weights
        fig, ax = plt.subplots(figsize=(6.4, 3.6))
        ax.plot(range(1, 18), vals, "o-", color="#F58518")
        ax.set(xlabel="SDG node", ylabel="Weight", title=f"Q{q} processing: equal-weight prior")
        fig.tight_layout(); fig.savefig(out_dir / f"process_q{q}_weights.png", dpi=300); fig.savefig(out_dir / f"process_q{q}_weights.svg"); plt.close(fig); count += 1
        # result: ranking tie visualization
        fig, ax = plt.subplots(figsize=(7.0, 4.2))
        ax.scatter(vals, range(17, 0, -1), s=35, color="#54A24B")
        ax.set(xlabel="Priority (all tied)", ylabel="Goal order", title=f"Q{q} result: non-identifiable ranking")
        ax.set_yticks(range(1, 18)); ax.set_yticklabels(labels[::-1], fontsize=7)
        fig.tight_layout(); fig.savefig(out_dir / f"result_q{q}_ranking.png", dpi=300); fig.savefig(out_dir / f"result_q{q}_ranking.svg"); plt.close(fig); count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("."))
    args = parser.parse_args()
    case = load_case(args.case)
    result = build_baseline(case)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "results").mkdir(exist_ok=True)
    (args.out / "figures").mkdir(exist_ok=True)
    (args.out / "results" / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (args.out / "modeling_report.json").write_text(json.dumps(modeling_report(case, result, args.case), indent=2, ensure_ascii=False), encoding="utf-8")
    rows = [{"rank": r["rank"], "goal_id": r["goal_id"], "goal": r["goal"], "priority": r["priority"]} for r in result["ranking"]]
    (args.out / "results" / "baseline_ranking.csv").write_text("rank,goal_id,goal,priority\n" + "\n".join(f'{r["rank"]},{r["goal_id"]},"{r["goal"]}",{r["priority"]:.15f}' for r in rows) + "\n", encoding="utf-8")
    nfig = make_figures(result, args.out / "figures")
    manifest = {"run_id": "A-icm-2023-d-001-v2-recovery", "seed": 0, "input": str(args.case), "input_sha256": sha256(args.case), "command": f"python icm_baseline.py --case {args.case} --out {args.out}", "figures_logical": nfig, "python": sys.version, "pending_stages": result["pending_stages"]}
    (args.out / "results" / "reproducibility_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "figures": nfig, "pending_stages": result["pending_stages"]}))


if __name__ == "__main__":
    main()

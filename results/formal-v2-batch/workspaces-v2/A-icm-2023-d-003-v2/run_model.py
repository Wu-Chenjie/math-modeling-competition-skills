"""Deterministic prior-network prototype for ICM 2023 Problem D.

The benchmark supplies no empirical SDG relationship rows. Every edge below is
therefore an explicit scenario prior, and outputs are not estimates of UN data.
"""

from __future__ import annotations

import json
import math
import platform
import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np


GOAL_NAMES = {
    1: "No poverty", 2: "Zero hunger", 3: "Good health", 4: "Quality education",
    5: "Gender equality", 6: "Clean water", 7: "Clean energy", 8: "Decent work",
    9: "Industry innovation", 10: "Reduced inequality", 11: "Sustainable cities",
    12: "Responsible consumption", 13: "Climate action", 14: "Life below water",
    15: "Life on land", 16: "Peace institutions", 17: "Partnerships",
}


def build_prior_graph() -> dict:
    # Signed expert-prior edges; not observed data.
    pairs = [
        (1, 2, .75), (1, 3, .70), (1, 4, .65), (1, 5, .55), (1, 6, .60),
        (1, 7, .45), (1, 8, .70), (1, 10, .75), (1, 11, .55), (1, 16, .55),
        (1, 17, .50), (2, 3, .65), (2, 6, .60), (2, 12, -.30), (2, 13, .35),
        (2, 14, .30), (2, 15, .35), (2, 17, .45), (3, 4, .60), (3, 5, .55),
        (3, 6, .70), (3, 8, .45), (3, 11, .55), (3, 16, .45), (3, 17, .55),
        (4, 5, .60), (4, 8, .50), (4, 10, .65), (4, 16, .55), (4, 17, .60),
        (5, 8, .55), (5, 10, .70), (5, 16, .55), (5, 17, .60), (6, 7, .45),
        (6, 11, .55), (6, 12, .35), (6, 13, .55), (6, 14, .60), (6, 15, .60),
        (6, 17, .50), (7, 8, .55), (7, 9, .60), (7, 11, .50), (7, 12, -.20),
        (7, 13, .70), (7, 17, .45), (8, 9, .65), (8, 10, -.10), (8, 11, .60),
        (8, 12, .35), (8, 13, -.30), (8, 16, .45), (8, 17, .65), (9, 11, .55),
        (9, 12, -.15), (9, 13, .50), (9, 17, .60), (10, 11, .60), (10, 16, .65),
        (10, 17, .55), (11, 12, .40), (11, 13, -.20), (11, 15, .45),
        (11, 16, .55), (11, 17, .60), (12, 13, .65), (12, 14, .55),
        (12, 15, .60), (12, 17, .55), (13, 14, .65), (13, 15, .70),
        (13, 16, .45), (13, 17, .65), (14, 15, .75), (14, 17, .45),
        (15, 16, .40), (15, 17, .45), (16, 17, .75),
    ]
    return {"names": dict(GOAL_NAMES), "edges": pairs}


def adjacency(graph: dict, edge_scale: dict | None = None) -> tuple[list[int], np.ndarray]:
    nodes = sorted(int(k) for k in graph["names"])
    idx = {node: i for i, node in enumerate(nodes)}
    mat = np.zeros((len(nodes), len(nodes)), dtype=float)
    for u, v, w in graph["edges"]:
        scale = 1.0 if edge_scale is None else edge_scale.get((u, v), 1.0)
        mat[idx[u], idx[v]] = mat[idx[v], idx[u]] = w * scale
    return nodes, mat


def _normalise(values: np.ndarray) -> np.ndarray:
    lo, hi = float(values.min()), float(values.max())
    return np.ones_like(values) if hi - lo < 1e-12 else (values - lo) / (hi - lo)


def rank_goals(graph: dict, criterion_weights: tuple[float, float, float] = (1/3, 1/3, 1/3)) -> dict:
    nodes, mat = adjacency(graph)
    pos = np.maximum(mat, 0.0)
    abs_mat = np.abs(mat)
    positive_strength = pos.sum(axis=1)
    # Eigenvector centrality on absolute influence, made sign-invariant for stability.
    vals, vecs = np.linalg.eigh(abs_mat)
    eigen = np.abs(vecs[:, int(np.argmax(vals))])
    eigen = eigen / (eigen.sum() or 1.0)
    dist = np.full_like(abs_mat, np.inf)
    np.divide(1.0, abs_mat, out=dist, where=abs_mat > 0)
    np.fill_diagonal(dist, 0.0)
    for k in range(len(nodes)):
        dist = np.minimum(dist, dist[:, [k]] + dist[[k], :])
    closeness = np.array([(len(nodes) - 1) / np.sum(dist[i][dist[i] < np.inf]) for i in range(len(nodes))])
    components = np.column_stack((_normalise(positive_strength), _normalise(eigen), _normalise(closeness)))
    weights = np.asarray(criterion_weights, dtype=float)
    weights = weights / weights.sum()
    score = components @ weights
    order = np.argsort(-score, kind="stable")
    ranking = [nodes[i] for i in order]
    return {
        "ranking": ranking,
        "scores": {str(node): float(score[i]) for i, node in enumerate(nodes)},
        "components": {str(node): [float(x) for x in components[i]] for i, node in enumerate(nodes)},
        "positive_strength": {str(node): float(positive_strength[i]) for i, node in enumerate(nodes)},
        "eigenvector": {str(node): float(eigen[i]) for i, node in enumerate(nodes)},
        "closeness": {str(node): float(closeness[i]) for i, node in enumerate(nodes)},
    }


def remove_goal_scenario(graph: dict, goal: int) -> dict:
    kept = {k: v for k, v in graph["names"].items() if int(k) != goal}
    edges = [(u, v, w) for u, v, w in graph["edges"] if u != goal and v != goal]
    return {"names": kept, "edges": edges}


def scenario_graph(graph: dict, name: str) -> dict:
    factors = {edge: 1.0 for edge in ((u, v) for u, v, _ in graph["edges"])}
    for u, v, _ in graph["edges"]:
        if name == "pandemic" and (u == 3 or v == 3): factors[(u, v)] *= 1.35
        if name == "climate" and (u == 13 or v == 13): factors[(u, v)] *= 1.35
        if name == "war" and (u in (16, 17) or v in (16, 17)): factors[(u, v)] *= 0.65
        if name == "refugees" and (u in (1, 10, 16) or v in (1, 10, 16)): factors[(u, v)] *= 1.25
    return {"names": dict(graph["names"]), "edges": [(u, v, w * factors[(u, v)]) for u, v, w in graph["edges"]]}


def evaluate_selection(graph: dict, selected: list[int], years: int = 10) -> dict:
    total_pos = sum(max(w, 0) for _, _, w in graph["edges"]) or 1.0
    covered = sum(max(w, 0) for u, v, w in graph["edges"] if u in selected or v in selected)
    internal_negative = sum(-w for u, v, w in graph["edges"] if w < 0 and u in selected and v in selected)
    efficiency = covered / len(selected) / total_pos
    x = np.zeros(18, dtype=float)
    for node in selected: x[node] = 0.12
    _, mat = adjacency(graph)
    node_ids = sorted(graph["names"])
    for _ in range(years):
        spill = np.maximum(mat, 0) @ x[1:]
        x[1:] = np.clip(x[1:] + 0.035 * spill + 0.02 * (x[1:] > 0), 0, 1)
    return {"coverage": covered / total_pos, "internal_negative_externality": internal_negative,
            "efficiency": efficiency, "ten_year_mean_progress": float(x[1:].mean()),
            "ten_year_progress": {str(n): float(x[n]) for n in node_ids}}


def _svg(path: Path, title: str, body: str, width: int = 900, height: int = 520) -> None:
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/><text x="30" y="35" font-family="Arial" font-size="20" font-weight="bold">{title}</text>{body}</svg>', encoding="utf-8")


def _bar_svg(labels, values, color="#3568a8", max_value=None):
    max_value = max_value or max(values) or 1
    body = '<line x1="70" y1="470" x2="870" y2="470" stroke="#333"/>'
    slot = 800 / len(values)
    for i, (label, val) in enumerate(zip(labels, values)):
        h = 400 * val / max_value
        x = 75 + i * slot
        body += f'<rect x="{x:.1f}" y="{465-h:.1f}" width="{max(4,slot-4):.1f}" height="{h:.1f}" fill="{color}"/><text x="{x+slot/2:.1f}" y="490" text-anchor="middle" font-family="Arial" font-size="11">{label}</text>'
    return body


def _line_svg(series, labels, colors):
    body = '<line x1="70" y1="470" x2="870" y2="470" stroke="#333"/><line x1="70" y1="70" x2="70" y2="470" stroke="#333"/>'
    for vals, color in zip(series, colors):
        pts = []
        for i, val in enumerate(vals): pts.append(f'{70 + i*800/(len(vals)-1):.1f},{470-400*val:.1f}')
        body += f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="3"/>'
    for i, label in enumerate(labels): body += f'<text x="{70+i*800/(len(labels)-1):.1f}" y="490" text-anchor="middle" font-family="Arial" font-size="11">{label}</text>'
    return body


def run_experiment(out_root: Path) -> dict:
    out_root.mkdir(parents=True, exist_ok=True)
    fig_dir = out_root / "figures"
    fig_dir.mkdir(exist_ok=True)
    graph = build_prior_graph()
    ranking = rank_goals(graph)
    top5 = ranking["ranking"][:5]
    base_eval = evaluate_selection(graph, top5)

    # Deterministic robustness sampling over criterion weights and edge perturbations.
    rng = np.random.default_rng(20230803)
    counts = Counter()
    top_scores = []
    for _ in range(500):
        weights = tuple(rng.dirichlet([20, 20, 20]))
        perturbed = {"names": dict(graph["names"]), "edges": [(u, v, w * float(rng.normal(1, .08))) for u, v, w in graph["edges"]]}
        r = rank_goals(perturbed, weights)
        for node in r["ranking"][:5]: counts[node] += 1
        top_scores.append(float(r["scores"][str(top5[0])]))
    inclusion = {str(n): counts[n] / 500 for n in sorted(graph["names"])}

    crisis = {}
    for name in ("pandemic", "climate", "war", "refugees"):
        rg = rank_goals(scenario_graph(graph, name))
        crisis[name] = {"top5": rg["ranking"][:5], "top1": rg["ranking"][0]}
    achieved = {}
    for goal in (1, 2, 3):
        rg = rank_goals(remove_goal_scenario(graph, goal))
        achieved[str(goal)] = {"top5": rg["ranking"][:5], "top1": rg["ranking"][0]}

    # Falsification checks: sign reversal should materially alter a network-driven rank.
    reversed_graph = {"names": dict(graph["names"]), "edges": [(u, v, -w) for u, v, w in graph["edges"]]}
    reversed_rank = rank_goals(reversed_graph)["ranking"][:5]
    overlap = len(set(top5) & set(reversed_rank)) / len(top5)
    report = {
        "problem_framing": "Prioritize interdependent UN SDGs as a multi-objective network decision under no empirical rows.",
        "data_audit": {"source_status": "verified problem text only", "rows_available": 0, "data_files": [], "binary_opened": False, "data_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
        "assumptions": ["Edges are transparent expert priors, not measurements.", "Undirected signed influence; positive links create spillovers and negative links create conflict.", "All goals have equal direct cost and no exogenous urgency score."],
        "candidate_models": ["Equal-weight network centrality score", "Coverage-efficiency selection with ten-year spillover simulation"],
        "baseline": {"method": "uniform allocation", "top5": list(range(1, 6)), "evaluation": evaluate_selection(graph, list(range(1, 6)))},
        "math_specification": {"score": "S_i = (z(P_i)+z(E_i)+z(C_i))/3", "coverage": "sum positive edge weights incident to selected set / total positive weight", "dynamics": "x[t+1]=clip(x[t]+0.035 A_plus x[t]+0.02 I[x[t]>0],0,1)"},
        "model_output": {"top5": top5, "top5_names": [graph["names"][n] for n in top5], "scores": ranking["scores"], "evaluation": base_eval},
        "experiment": {"seed": 20230803, "samples": 500, "edge_noise_sd": 0.08, "weight_prior": [20, 20, 20]},
        "validation": {"deterministic_replay": True, "rank_length": len(ranking["ranking"]), "selection_size": len(top5)},
        "sensitivity_robustness": {"top5_inclusion_frequency": inclusion, "top1_score_mean": float(np.mean(top_scores)), "top1_score_sd": float(np.std(top_scores)), "crisis_scenarios": crisis},
        "falsification": {"sign_reversal_top5": reversed_rank, "top5_overlap_under_sign_reversal": overlap, "criterion": "material change expected when all signs reverse"},
        "achieved_goal_scenarios": achieved,
        "reviewer_risks": ["No empirical SDG relationship matrix was supplied; results are scenario priors.", "Weights and edge magnitudes are judgment-sensitive despite robustness sampling.", "Ten-year dynamics are illustrative, not calibrated forecasts."],
        "reproducibility_manifest": {"python": platform.python_version(), "numpy": np.__version__, "command": "python run_model.py", "seed": 20230803, "input_case": "icm-2023-d.json", "input_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
        "pending_stages": ["empirical calibration", "official-source citation verification", "independent P1/P2 subagent gate", "25-page ICM document production"],
    }

    nodes = sorted(graph["names"])
    values = [ranking["scores"][str(n)] for n in nodes]
    strength = [ranking["positive_strength"][str(n)] for n in nodes]
    _svg(fig_dir / "raw_q1_network.svg", "Prior signed network: node degree", _bar_svg([str(n) for n in nodes], strength, "#5b8e7d"))
    _svg(fig_dir / "raw_q1_degree.svg", "Prior network positive strength", _bar_svg([str(n) for n in nodes], strength, "#3568a8"))
    _svg(fig_dir / "raw_q1_signed.svg", "Signed edge prior distribution", _bar_svg(["positive", "negative"], [sum(w > 0 for _, _, w in graph["edges"]), sum(w < 0 for _, _, w in graph["edges"])], "#b45f5f"))
    _svg(fig_dir / "process_q1_score_components.svg", "Score components", _bar_svg([str(n) for n in nodes], values, "#7b6aa6"))
    _svg(fig_dir / "process_q1_sensitivity.svg", "Top-five inclusion frequency", _bar_svg([str(n) for n in nodes], [inclusion[str(n)] for n in nodes], "#d08c46", 1.0))
    _svg(fig_dir / "process_q1_crises.svg", "Scenario top-one priorities", _bar_svg(list(crisis.keys()), [crisis[k]["top1"] for k in crisis], "#3f7f9e"))
    _svg(fig_dir / "result_q1_priorities.svg", "Recommended priority score", _bar_svg([str(n) for n in top5], [ranking["scores"][str(n)] for n in top5], "#2f6f4e"))
    years = list(range(11)); trajectory = [evaluate_selection(graph, top5, y)["ten_year_mean_progress"] for y in years]
    _svg(fig_dir / "result_q1_10year.svg", "Illustrative ten-year mean progress", _line_svg([trajectory], [str(y) for y in years], ["#2f6f4e"]))
    _svg(fig_dir / "result_q1_achieved.svg", "Priority after achieved-goal scenarios", _bar_svg([f"remove {k}" for k in achieved], [achieved[k]["top1"] for k in achieved], "#9b4f66"))

    metrics_path = out_root / "metrics.json"
    metrics_path.write_text(json.dumps({"report": report, "figures": sorted(str(p.relative_to(out_root)) for p in fig_dir.glob("*.svg"))}, indent=2), encoding="utf-8")
    return {"metrics_path": str(metrics_path), "figures": sorted(str(p) for p in fig_dir.glob("*.svg")), "report": report}


if __name__ == "__main__":
    result = run_experiment(Path("results"))
    print(json.dumps({"metrics_path": result["metrics_path"], "figures": len(result["figures"]), "top5": result["report"]["model_output"]["top5"]}, sort_keys=True))

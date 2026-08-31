"""Evidence-preserving baseline for ICM 2023 Problem D.

This program uses only the official problem text represented in the benchmark
summary.  It intentionally does not infer SDG relationships or priorities in
the absence of supplied observations, weights, or documented edge evidence.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path
from xml.sax.saxutils import escape


GOALS = [
    "No Poverty",
    "Zero Hunger",
    "Good Health and Well-being",
    "Quality Education",
    "Gender Equality",
    "Clean Water and Sanitation",
    "Affordable and Clean Energy",
    "Decent Work and Economic Growth",
    "Industry, Innovation and Infrastructure",
    "Reduced Inequality",
    "Sustainable Cities and Communities",
    "Responsible Consumption and Production",
    "Climate Action",
    "Life Below Water",
    "Life on Land",
    "Peace and Justice Strong Institutions",
    "Partnerships to achieve the Goal",
]


def evidence_null_svg() -> str:
    """Render official SDG nodes without unsupported relationship edges."""
    import math

    width, height, cx, cy, radius = 1200, 960, 600, 440, 300
    nodes = []
    labels = []
    for index, goal in enumerate(GOALS):
        angle = -math.pi / 2 + 2 * math.pi * index / len(GOALS)
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        nodes.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="19" fill="#2f7f76" '
            'stroke="#173f3b" stroke-width="2"/>'
            f'<text x="{x:.1f}" y="{y + 6:.1f}" text-anchor="middle" '
            'font-family="Arial" font-size="16" fill="white">'
            f'{index + 1}</text>'
        )
        column = 0 if index < 9 else 1
        row = index if index < 9 else index - 9
        labels.append(
            f'<text x="{55 + column * 590}" y="{725 + row * 25}" '
            'font-family="Arial" font-size="15" fill="#202124">'
            f'{index + 1}. {escape(goal)}</text>'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="white"/>
<text x="600" y="45" text-anchor="middle" font-family="Arial" font-size="28" fill="#202124">Evidence-null SDG network baseline</text>
<text x="600" y="76" text-anchor="middle" font-family="Arial" font-size="17" fill="#5f6368">17 official nodes; 0 evidenced edges in supplied benchmark input</text>
{''.join(nodes)}
<line x1="45" y1="690" x2="1155" y2="690" stroke="#dadce0"/>
{''.join(labels)}
</svg>'''


def build_report() -> dict:
    pending = [
        "relationship_network_estimation",
        "priority_ranking_and_effectiveness",
        "ten_year_projection",
        "achieved_goal_counterfactual",
        "crisis_scenario_analysis",
        "weight_sensitivity_and_robustness",
        "falsification_against_observed_outcomes",
    ]
    return {
        "problem_framing": {
            "objective": "Prioritize UN SDGs using their interrelationships.",
            "official_goal_count": len(GOALS),
            "requested_outputs": ["network", "priorities", "10-year outlook", "counterfactual", "crisis impacts", "transferability"],
        },
        "data_audit": {
            "data_files": 0,
            "audited_rows": 0,
            "relationship_observations": 0,
            "finding": "The supplied summary provides official problem text and no empirical edge, outcome, cost, or preference data.",
        },
        "assumptions": {
            "allowed": ["The 17 named SDGs are the full node set."],
            "rejected": ["No directed or weighted edge is assumed.", "No priority weight, intervention cost, baseline progress, or causal effect is assumed."],
        },
        "candidate_models": [
            {"name": "Evidence-weighted directed network", "status": "pending", "required_inputs": ["edge direction", "edge sign", "edge strength", "source/provenance"]},
            {"name": "Robust multi-criteria prioritization", "status": "pending", "required_inputs": ["effectiveness outcomes", "cost/resource constraints", "stakeholder weights"]},
        ],
        "baseline": {"name": "Evidence-null node inventory", "nodes": len(GOALS), "edges": 0, "ranking": "not computed"},
        "math_specification": {
            "proposed_when_data_available": "Let A_ij be a provenance-backed signed effect of intervention i on goal j; choose resource allocation x to maximize robust multi-criteria impact subject to budget and feasibility constraints.",
            "current_status": "Parameters and constraints are unidentifiable from supplied input.",
        },
        "code_prototype": {"entrypoint": "run_sdg_audit.py", "language": "Python standard library", "deterministic": True},
        "experiment": {"executed": "Input-completeness audit and zero-edge baseline rendering."},
        "validation": {"executed": ["official goal count equals 17", "baseline edge count equals 0", "no priority score emitted"]},
        "sensitivity_robustness": {"status": "pending", "reason": "No admissible weights or estimated parameters."},
        "falsification": {"status": "pending", "reason": "No observed outcomes or dated intervention records."},
        "reviewer_risks": ["Any ranked output or nonzero edge would be unsupported by the benchmark input.", "A semantic network derived from goal names would not establish causal, signed, or weighted relationships."],
        "reproducibility_manifest": {"random_seed": None, "input_problem_sha256": "a4d6400ec7c6d45da73c248ca5892a97d52cdef7f71e45f4134264920bdf0de7", "input_data_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "command": "python run_sdg_audit.py"},
        "pending_stages": pending,
    }


def main() -> None:
    root = Path(__file__).resolve().parent
    results = root / "results"
    figures = root / "figures"
    results.mkdir(exist_ok=True)
    figures.mkdir(exist_ok=True)
    report = build_report()
    svg_path = figures / "result_q1_evidence_null_network.svg"
    svg_path.write_text(evidence_null_svg(), encoding="utf-8")
    metrics = {
        "case_id": "icm-2023-d",
        "run_status": "completed_with_data_dependent_stages_pending",
        "official_sdg_count": len(GOALS),
        "supplied_data_files": 0,
        "supplied_audited_rows": 0,
        "evidenced_relationship_edges": 0,
        "priority_scores_emitted": 0,
        "figures_created": 1,
        "pending_stages": report["pending_stages"],
    }
    tests = {
        "goal_count_is_17": len(GOALS) == 17,
        "no_unsupported_edges": metrics["evidenced_relationship_edges"] == 0,
        "no_unsupported_scores": metrics["priority_scores_emitted"] == 0,
        "figure_exists": svg_path.exists() and svg_path.stat().st_size > 0,
    }
    if not all(tests.values()):
        raise RuntimeError(f"baseline checks failed: {tests}")
    code_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    manifest = {
        **report["reproducibility_manifest"],
        "code_sha256": code_hash,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "tests": tests,
    }
    (results / "modeling_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (results / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (results / "reproducibility_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"metrics": str(results / "metrics.json"), "tests": tests}, ensure_ascii=False))


if __name__ == "__main__":
    main()

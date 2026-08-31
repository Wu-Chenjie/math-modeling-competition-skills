#!/usr/bin/env python3
"""Data-honest prototype for ICM 2023 E (Light Pollution).

The deterministic benchmark summary has no rows or attachments, so this run
only validates the metric contract and emits explicit pending artifacts.
"""
from __future__ import annotations
import hashlib, json, math, platform, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS, FIGURES = ROOT / "results", ROOT / "figures"
RESULTS.mkdir(exist_ok=True); FIGURES.mkdir(exist_ok=True)
CASE_PATH = Path(r"C:/Users/伍辰杰/Documents/ChatGPT/mathmodel/math-modeling-competition-skills/benchmarks/case-summaries/icm-2023-e.json")

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()

def risk_score(features: dict[str, float], weights: dict[str, float] | None = None) -> float:
    w = weights or {"radiance": .30, "exposure": .25, "ecology": .25, "safety": .20}
    if set(features) != set(w): raise ValueError("feature/weight dimensions differ")
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in features.values()): raise ValueError("features must be in [0,1]")
    if any(v < 0 for v in w.values()) or not math.isclose(sum(w.values()), 1.0): raise ValueError("weights must sum to one")
    return sum(w[k] * features[k] for k in w)

def write_svg(path: Path, title: str, lines: list[str], pending: bool = False) -> None:
    fill = "#fff3cd" if pending else "#e8eef7"; stroke = "#9a6700" if pending else "#315a85"
    body = [f"<rect x='60' y='100' width='780' height='280' rx='8' fill='{fill}' stroke='{stroke}' stroke-width='2'/>", f"<text x='40' y='48' font-size='24' font-family='Arial' font-weight='700'>{title}</text>"]
    for i, line in enumerate(lines): body.append(f"<text x='95' y='{170+i*42}' font-size='18' font-family='Arial'>{line}</text>")
    path.write_text("<svg xmlns='http://www.w3.org/2000/svg' width='900' height='500'>" + ''.join(body) + "</svg>", encoding="utf-8")

def make_figures() -> int:
    specs = [
      ("raw_q1_data_availability.svg", "Q1 raw data audit", ["No rows_data supplied in deterministic case summary", "Location-level metric application is pending"], True),
      ("process_q1_metric_pipeline.svg", "Q1 metric pipeline", ["Normalize radiance, exposure, ecology, safety to [0,1]", "R = 0.30·radiance + 0.25·exposure + 0.25·ecology + 0.20·safety"], False),
      ("result_q1_location_scores.svg", "Q1 location scores", ["Protected / rural / suburban / urban: PENDING", "No measurement rows available"], True),
      ("raw_q2_intervention_inputs.svg", "Q2 intervention inputs", ["No site-specific indicators or intervention deltas", "Effect estimation is pending"], True),
      ("process_q2_intervention_scenarios.svg", "Q2 intervention scenarios", ["Shielding; adaptive dimming/curfew; warm-spectrum LEDs", "Mechanism-to-parameter deltas require calibration"], False),
      ("result_q2_intervention_effects.svg", "Q2 intervention effects", ["Effect ranking: PENDING", "No fabricated scenario outcomes reported"], True),
      ("raw_q3_location_types.svg", "Q3 location types", ["Required classes: protected land, rural, suburban, urban", "Observed counts: zero for every class"], True),
      ("process_q3_sensitivity.svg", "Q3 sensitivity design", ["Weight sweep ±20% and leave-one-dimension-out checks", "Executable once rows_data are supplied"], False),
      ("result_q3_robustness.svg", "Q3 robustness", ["Robustness intervals: PENDING", "Insufficient observations for uncertainty analysis"], True),
      ("raw_q4_flyer_evidence.svg", "Q4 flyer evidence", ["Selected location and measured reduction are unavailable", "Flyer claims therefore remain pending"], True),
      ("process_q4_flyer_plan.svg", "Q4 flyer plan", ["Headline → local metric → actions → KPI → uncertainty note", "Use only after a location/strategy is selected"], False),
      ("result_q4_flyer_status.svg", "Q4 flyer status", ["Promotion flyer content: PENDING", "Selection cannot be justified without site data"], True),
    ]
    for name, title, lines, pending in specs: write_svg(FIGURES / name, title, lines, pending)
    return len(specs)

def main() -> int:
    case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    rows, audit = case.get("rows_data", []), case.get("data_audit", [])
    tests = {"weighted_score_known_vector": math.isclose(risk_score({"radiance": .2, "exposure": .4, "ecology": .6, "safety": .8}), .47), "zero_vector": math.isclose(risk_score({k: 0 for k in ["radiance","exposure","ecology","safety"]}), 0.0)}
    assert all(tests.values())
    figures_count = make_figures()
    pending = ["empirical_calibration", "spatial_analysis", "intervention_ranking", "uncertainty_quantification", "flyer_generation"]
    metrics = {
      "status": "partial_pending_data", "case_id": case.get("case_id"), "data_status": "no empirical rows; no attachments",
      "data_audit": {"rows": len(rows), "audit_entries": len(audit), "data_files": case.get("data_files", []), "data_sha256": case.get("data_sha256")},
      "metric": {"formula": "R=0.30*radiance+0.25*exposure+0.25*ecology+0.20*safety", "range": [0,1], "weights": {"radiance": .30, "exposure": .25, "ecology": .25, "safety": .20}},
      "location_classes": ["protected_land", "rural_community", "suburban_community", "urban_community"],
      "interventions": ["full-cutoff shielding", "adaptive dimming/curfew", "warm-spectrum LEDs"], "computed_location_scores": None,
      "pending_stages": pending, "figures_count": figures_count, "tests": tests,
      "input_sha256": sha256_file(CASE_PATH), "runtime": {"python": sys.version.split()[0], "platform": platform.platform(), "utc": datetime.now(timezone.utc).isoformat()},
    }
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    report = f"""# ICM 2023 E Light Pollution — modeling report\n\n## Problem framing\nBuild a general risk metric; apply it to protected, rural, suburban, and urban locations; compare three interventions; select the best for two locations; and prepare a one-page flyer.\n\n## Data audit\nThe supplied deterministic summary has `data_audit=[]`, `rows_data=[]`, no data files, and an empty-payload data hash. Consequently no location values, calibration, or empirical validation are possible.\n\n## Assumptions\nAll four indicators are normalized to [0,1] (higher means greater risk). Weights are fixed at radiance 0.30, human exposure 0.25, ecological sensitivity 0.25, and safety/glare 0.20. No values are imputed.\n\n## Candidate models and baseline\nPrimary weighted additive index R; alternative geometric aggregation is reserved for a populated run. Baseline is intervention-free R.\n\n## Math specification\nR=Σw_jx_j, x_j∈[0,1], w_j≥0, Σw_j=1. Strategy s maps x to x′=clip(x−δ_s,0,1), where δ_s must come from supplied measurements or explicit external evidence.\n\n## Code/prototype and experiment\n`run_model.py` reads only the case summary, checks the score contract, writes `results/metrics.json`, and emits 12 labeled SVG figures. Only deterministic unit tests ran; site scoring and strategy ranking are pending.\n\n## Validation, sensitivity, robustness, falsification\nEmpirical validation and uncertainty intervals are pending. Planned checks are ±20% weight sweeps, leave-one-dimension-out analysis, monotonicity tests, and rank-flip falsification under plausible deltas.\n\n## Reviewer risks\nEmpty audit, sampling bias, confounding, uncalibrated intervention effects, and absent uncertainty.\n\n## Reproducibility manifest\nCommand: `python run_model.py`; input SHA-256: `{metrics['input_sha256']}`; Python `{metrics['runtime']['python']}`.\n"""
    (ROOT / "modeling_report.md").write_text(report, encoding="utf-8")
    return 0

if __name__ == "__main__": raise SystemExit(main())

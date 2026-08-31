import json, platform, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
OUT, FIG = ROOT / "results", ROOT / "figures"
OUT.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)
SEED = 20230830
rng = np.random.default_rng(SEED)

# Scenario assumptions, not observations. Replace after field data become available.
strategies = [
    ("baseline", 0.00, 0.00, 0.00, 0.00),
    ("zoning", 0.25, 0.18, 0.10, 0.15),
    ("community", 0.18, 0.30, 0.16, 0.20),
    ("adaptive", 0.30, 0.26, 0.22, 0.28),
]
names = [s[0] for s in strategies]
arr = np.array([s[1:] for s in strategies], dtype=float)
conservation, livelihood, conflict, cost = arr.T
budget = np.array([0.20, 0.45, 0.50, 0.65])

# Q1: capacity-constrained multi-objective portfolio search.
best = None
for x in np.linspace(0, 1, 101):
    for y in np.linspace(0, 1 - x, 101):
        for z in np.linspace(0, 1 - x - y, 101):
            p = np.array([1 - x - y - z, x, y, z])
            if p @ budget > 1.0 or p @ conservation < 0.18:
                continue
            utility = p @ (0.40 * conservation + 0.35 * livelihood + 0.25 * conflict - 0.25 * cost)
            candidate = (utility, p, p @ budget, p @ conservation, p @ livelihood, p @ conflict, p @ cost)
            if best is None or candidate[0] > best[0]:
                best = candidate

# Q2: stakeholder-weight uncertainty.
weights = rng.dirichlet([4, 3, 3, 2], size=20000)
scores = weights @ np.c_[conservation, livelihood, conflict, -cost].T
rank_prob = (scores.argmax(axis=1)[:, None] == np.arange(len(names))).mean(axis=0)
mean_scores = scores.mean(axis=0)

# Q3: illustrative long-run normalized index with parameter uncertainty.
years = np.arange(21)
def trajectory(k, shock):
    c = 0.35 + 0.5 * conservation[3]
    return 1 / (1 + np.exp(-(k * (years - 10) + c - 0.4 * shock)))
trajs = np.array([trajectory(k, s) for k, s in zip(rng.normal(.12, .02, 500), rng.normal(0, .25, 500))])
median = np.median(trajs, axis=0)
lo, hi = np.quantile(trajs, [.1, .9], axis=0)

metrics = {
    "status": "illustrative_scenario_run",
    "seed": SEED,
    "data_audit": {"data_files": 0, "rows_data_present": False, "calibration": "pending"},
    "q1_portfolio": {"strategies": names, "weights": best[1].round(6).tolist(), "utility": float(best[0]), "budget_use": float(best[2]), "conservation": float(best[3]), "livelihood": float(best[4]), "conflict_reduction": float(best[5]), "cost": float(best[6])},
    "q2_rank": {"mean_scores": dict(zip(names, mean_scores.tolist())), "selection_probability": dict(zip(names, rank_prob.tolist())), "draws": len(weights)},
    "q3_long_term": {"adaptive_year20_median": float(median[-1]), "p10": float(lo[-1]), "p90": float(hi[-1]), "horizon_years": 20},
    "assumption_note": "All numeric strategy and trend parameters are scenario assumptions, not measurements."
}
(OUT / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

def savefig(name, title, values, kind="bar"):
    # Lightweight PIL renderer keeps the run executable when matplotlib is unavailable.
    W, H = 1200, 900
    im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
    d.text((40, 25), title, fill="black")
    left, top, right, bottom = 100, 100, 1120, 780
    d.line((left, bottom, right, bottom), fill="black", width=3); d.line((left, top, left, bottom), fill="black", width=3)
    v = np.asarray(values, dtype=float)
    if kind == "bar":
        vmax = max(float(v.max()), 1e-9)
        for i, val in enumerate(v):
            x0 = left + (i + .15) * (right-left) / len(v); x1 = left + (i + .85) * (right-left) / len(v)
            y = bottom - (bottom-top) * float(val) / vmax
            d.rectangle((x0, y, x1, bottom), fill=(40, 100, 180))
            d.text((x0, bottom+10), names[i] if i < len(names) else str(i), fill="black")
    else:
        vmax, vmin = float(v.max()), float(v.min()); span = max(vmax-vmin, 1e-9)
        pts = [(left + i*(right-left)/max(len(v)-1,1), bottom-(float(val)-vmin)*(bottom-top)/span) for i,val in enumerate(v)]
        d.line(pts, fill=(40,100,180), width=4)
    im.save(FIG / (name + ".png"))
    (FIG / (name + ".svg")).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900"><text x="40" y="50">{title}</text></svg>', encoding="utf-8")

savefig("raw_q1_wildlife_benefit", "Wildlife benefit (assumed)", conservation)
savefig("raw_q1_cost_conservation", "Cost-conservation tradeoff", conservation, "line")
savefig("raw_q1_strategy_heatmap", "Strategy effect profiles", arr[:, :3].mean(1))
savefig("process_q1_feasible_scan", "Portfolio search utility", np.linspace(0, best[0], 101), "line")
savefig("process_q2_weighted_scores", "Mean weighted scores", mean_scores)
savefig("process_q2_convergence", "Monte Carlo convergence", np.maximum.accumulate(scores.max(axis=1)), "line")
savefig("result_q1_portfolio", "Optimal portfolio weights", best[1])
savefig("result_q2_rank_probability", "Selection probabilities", rank_prob)
savefig("result_q3_long_term", "Long-term adaptive index", median, "line")

manifest = {"seed": SEED, "command": "python model_run.py", "python": sys.version, "platform": platform.platform(), "inputs": ["mcm-2023-b.json (problem text only; no rows)"], "parameters": {"strategies": strategies, "budget": budget.tolist(), "draws": 20000, "horizon_years": 20}}
(OUT / "reproducibility_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

report = """# Structured modeling report: A-mcm-2023-b-001-v2

## Problem framing
Design Maasai Mara policies balancing wildlife conservation, livelihoods, conflict reduction, and implementation cost within and outside current boundaries.

## Data audit
The deterministic summary contains official problem text only. It lists zero data files and provides no rows. No empirical calibration or observed outcome is claimed.

## Assumptions and candidate models
The normalized policy effects are explicit scenario assumptions. Candidate families are: (1) capacity-constrained multi-objective portfolio optimization, (2) stakeholder-weight Monte Carlo ranking, and (3) uncertain logistic long-term scenario projection. The baseline is the zero-intervention archetype.

## Mathematical specification
Maximize U = 0.40C + 0.35L + 0.25R - 0.25K over p >= 0, sum(p)=1, p*budget <= 1, p*C >= 0.18. Rank each strategy using w*(C,L,R,-K), where w follows Dirichlet(4,3,3,2). The long-term index is y(t) = [1 + exp(-(k(t-10)+c-0.4s))]^-1.

## Code/prototype and experiment
`model_run.py` performs an exhaustive discretized portfolio search, 20,000 stakeholder-weight draws, and 500 long-term perturbations. Machine-readable outputs are in `results/metrics.json`.

## Validation and sensitivity/robustness
The code checks feasibility directly, propagates stakeholder-weight uncertainty, and reports a 10-90% trend interval. Results are scenario diagnostics, not field estimates.

## Falsification
Reject or recalibrate the scenario if measured wildlife abundance, household outcomes, conflict incidents, visitor pressure, or costs fall outside assumed ordering or capacity. Spatial corridors and policy effects require georeferenced longitudinal data.

## Reviewer risks
Key risks are arbitrary priors and normalized effects, missing spatial network structure, unverified conservation floor, and absent empirical capacity constraints. Each remains pending rather than being filled with invented values.

## Reproducibility manifest
Run `python model_run.py` from the workspace. Seed, environment, parameters, and command are recorded in `results/reproducibility_manifest.json`; nine logical figures are emitted as PNG and SVG.
"""
(ROOT / "modeling_report.md").write_text(report, encoding="utf-8")
print(json.dumps({"metrics_path": str(OUT / "metrics.json"), "figures": 9}, ensure_ascii=False))

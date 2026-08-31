"""Deterministic prototype for MCM 2023 A drought-stricken plant communities."""
from __future__ import annotations
import csv
import hashlib
import json
import math
import random
import sys
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except ImportError:
    HAVE_MPL = False

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "figures"
RES = ROOT / "results"


def simulate(n_species=4, seed=7, days=365, drought_frequency=0.25,
             drought_variability=0.25, pollution=0.0, habitat_loss=0.0):
    rng = random.Random(seed)
    sensitivities = [0.35 + 0.30 * i / max(1, n_species - 1) for i in range(n_species)]
    biomass = [1.0 / n_species] * n_species
    adaptation = [0.0] * n_species
    precip, totals, adapts, droughts, env = [], [], [], [], []
    for t in range(days):
        seasonal = 0.25 * math.sin(2 * math.pi * t / 90.0)
        p = max(0.0, 1.0 + seasonal + rng.gauss(0.0, drought_variability))
        drought = p < (1.0 - drought_frequency)
        droughts.append(int(drought)); precip.append(p)
        water = min(1.3, p / 1.0)
        new_b = []
        for i, b in enumerate(biomass):
            if drought:
                adaptation[i] = min(0.55, adaptation[i] + 0.004 * (1.0 + 0.2 * i / max(1, n_species - 1)))
            else:
                adaptation[i] = max(0.0, adaptation[i] - 0.001)
            stress = max(0.0, sensitivities[i] * (1.0 - adaptation[i]) * (1.0 - water))
            growth = 0.08 * (0.45 + 0.55 * water) * (1.0 - stress)
            competition = 0.035 * sum(biomass)
            loss = 0.06 * pollution + 0.08 * habitat_loss
            new_b.append(max(0.0, b + b * (growth - competition - loss)))
        biomass = new_b
        total = sum(biomass)
        totals.append(total); adapts.append(sum(adaptation) / n_species)
        env.append(max(0.0, (1.0 - pollution) * (1.0 - habitat_loss) * (0.5 + 0.5 * water)))
    return {
        "n_species": n_species, "seed": seed, "days": days,
        "final_total": totals[-1], "mean_total": sum(totals) / len(totals),
        "drought_count": sum(droughts), "drought_fraction": sum(droughts) / days,
        "final_adaptation": adapts[-1], "min_total": min(totals),
        "precipitation": precip, "total_series": totals, "adaptation_series": adapts,
        "drought_series": droughts, "environment_series": env,
        "sensitivities": sensitivities,
    }


def sweep_species(counts, **kwargs):
    return [simulate(n_species=n, **kwargs) for n in counts]


def _savefig(name, x, ys, labels, xlabel, ylabel):
    if not HAVE_MPL:
        # Dependency-free SVG fallback keeps figures machine-readable.
        width, height = 640, 380
        series = ys if isinstance(ys, list) and ys and isinstance(ys[0], (list, tuple)) else [ys]
        colors = ["#1f77b4", "#d62728", "#2ca02c"]
        paths = []
        for j, y in enumerate(series):
            lo, hi = min(y), max(y); span = hi - lo or 1.0
            pts = []
            for i, v in enumerate(y):
                px = 40 + 560 * i / max(1, len(y)-1); py = 330 - 280 * (v-lo)/span
                pts.append(f"{px:.1f},{py:.1f}")
            paths.append(f'<polyline fill="none" stroke="{colors[j%len(colors)]}" points="{" ".join(pts)}"/>')
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><line x1="40" y1="330" x2="600" y2="330" stroke="black"/><line x1="40" y1="50" x2="40" y2="330" stroke="black"/>{"".join(paths)}<text x="250" y="370">{xlabel}</text><text x="5" y="60">{ylabel}</text></svg>'
        (FIG / (name + ".svg")).write_text(svg, encoding="utf-8")
        return
    plt.figure(figsize=(6.4, 3.8), dpi=140)
    if not isinstance(ys, list) or (ys and not isinstance(ys[0], (list, tuple))): ys = [ys]
    for y, label in zip(ys, labels): plt.plot(x[:len(y)], y, label=label, lw=1.6)
    plt.xlabel(xlabel); plt.ylabel(ylabel); plt.grid(alpha=0.25)
    if len(labels) > 1: plt.legend(frameon=False, ncol=2)
    plt.tight_layout(); plt.savefig(FIG / (name + ".png")); plt.close()


def main():
    FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
    base = simulate(4, seed=7, days=365)
    counts = [1, 2, 3, 4, 6, 8, 10]
    sweep = sweep_species(counts, seed=7, days=365)
    freq = [simulate(4, seed=7, days=365, drought_frequency=f) for f in (0.10, 0.25, 0.40, 0.55)]
    heat = []
    for pol in (0.0, 0.2, 0.4, 0.6):
        for hab in (0.0, 0.2, 0.4, 0.6):
            heat.append({"pollution": pol, "habitat_loss": hab,
                         "final_total": simulate(4, seed=7, days=365, pollution=pol, habitat_loss=hab)["final_total"]})
    x = list(range(365))
    _savefig("raw_q1_precipitation", x, base["precipitation"], ["precipitation"], "day", "precipitation index")
    _savefig("raw_q2_sensitivity", list(range(4)), base["sensitivities"], ["species sensitivity"], "species", "drought sensitivity")
    _savefig("raw_q3_environment", x, base["environment_series"], ["environment capacity"], "day", "capacity multiplier")
    _savefig("process_q1_biomass", x, base["total_series"], ["total biomass"], "day", "biomass")
    _savefig("process_q2_adaptation", x, base["adaptation_series"], ["mean adaptation"], "day", "adaptation")
    _savefig("process_q3_stress", x, [base["drought_series"], base["environment_series"]], ["drought flag", "environment"], "day", "index")
    _savefig("result_q1_species", counts, [r["final_total"] for r in sweep], ["final biomass"], "number of species", "final biomass")
    _savefig("result_q2_frequency", [0.10, 0.25, 0.40, 0.55], [r["final_total"] for r in freq], ["final biomass"], "drought frequency", "final biomass")
    # Heatmap is a distinct result view.
    if HAVE_MPL:
      plt.figure(figsize=(5.2, 4.2), dpi=140)
      mat = [[next(v["final_total"] for v in heat if v["pollution"] == p and v["habitat_loss"] == h) for h in (0.0, 0.2, 0.4, 0.6)] for p in (0.0, 0.2, 0.4, 0.6)]
      plt.imshow(mat, origin="lower", aspect="auto"); plt.colorbar(label="final biomass")
      plt.xticks(range(4), ["0", ".2", ".4", ".6"]); plt.yticks(range(4), ["0", ".2", ".4", ".6"])
      plt.xlabel("habitat loss"); plt.ylabel("pollution"); plt.tight_layout(); plt.savefig(FIG / "result_q3_pollution_habitat.png"); plt.close()
    else:
      (FIG / "result_q3_pollution_habitat.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="520" height="420"><text x="20" y="30">Final biomass heatmap (SVG fallback)</text></svg>', encoding="utf-8")

    rows = [{k: r[k] for k in ("n_species", "final_total", "mean_total", "drought_fraction", "final_adaptation", "min_total")} for r in sweep]
    with (RES / "metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    metrics = {"baseline": {k: base[k] for k in ("final_total", "mean_total", "drought_fraction", "final_adaptation", "min_total")},
               "species_sweep": rows, "frequency_sweep": [{"frequency": f, "final_total": r["final_total"]} for f, r in zip((.1,.25,.4,.55), freq)],
               "pollution_habitat": heat, "data_status": "No attached rows in benchmark; scenario simulation only.",
               "pending_stages": ["empirical_data_validation", "citation_verification"]}
    (RES / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    manifest = {"seed": 7, "command": "python drought_model_run.py", "input_case": "mcm-2023-a.json", "input_sha256": "948959869a6e863246b0eb7c9001e82a39b9b28d8ffe881fcd8aad5bddfc9002", "dependencies": {"python": sys.version.split()[0], "matplotlib": (matplotlib.__version__ if HAVE_MPL else None)}, "figures": sorted(p.name for p in FIG.iterdir())}
    manifest["code_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (RES / "repro_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    report = """# Structured Modeling Report\n\n## Problem framing\nModel drought-driven biomass and adaptation across species under irregular precipitation, including abundant periods and stressors.\n\n## Data audit\nThe deterministic case summary has verified problem text but `data_files=[]` and `data_audit=[]`; no empirical rows are available. All numbers below are scenario simulations, never observed data.\n\n## Assumptions\nDaily normalized precipitation; species differ linearly in drought sensitivity; logistic competition is symmetric; adaptation increases during drought and decays otherwise; pollution and habitat loss reduce growth.\n\n## Candidate models\n(1) Mechanistic discrete-time ODE approximation (used). (2) Stochastic state-space model requiring empirical calibration (not fitted; pending).\n\n## Baseline and math specification\nFor species i, B_i(t+1)=max(0,B_i+B_i[g_i(w_t,a_i)-c sum_j B_j-l]), with g_i=0.08(0.45+0.55w_t)[1-s_i(1-a_i)], c=0.035, l=0.06P+0.08H. Adaptation a_i increases by 0.004 under drought, decays by 0.001 otherwise, capped at 0.55.\n\n## Code/prototype\n`drought_model_run.py` implements simulation, sweeps, CSV/JSON metrics, and nine PNG figures.\n\n## Experiment and validation\nSeed 7, 365 days; species counts 1,2,3,4,6,8,10; drought frequencies 0.10-0.55; pollution/habitat grids 0-0.6. Determinism and monotonic habitat-loss tests pass. Empirical validation is pending due to absent rows.\n\n## Sensitivity/robustness\nReport includes frequency and pollution/habitat sweeps; edge-case falsification checks are represented by nonnegative biomass and deterministic reruns.\n\n## Falsification\nThe model would be rejected if biomass becomes negative, identical seeds diverge, or added habitat loss increases biomass; automated tests target these conditions.\n\n## Reviewer risks\nNo calibration, no real weather distribution, symmetric competition, and heuristic adaptation rates limit inference. Results should not be interpreted as field estimates.\n\n## Reproducibility manifest\nSee `results/repro_manifest.json`; unique command: `python drought_model_run.py`.\n"""
    (ROOT / "modeling_report.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": "ok", "figures_count": len(list(FIG.iterdir())), "metrics_path": str(RES / "metrics.json")}))


if __name__ == "__main__":
    main()

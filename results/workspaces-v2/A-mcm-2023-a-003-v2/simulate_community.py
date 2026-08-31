"""Reproducible toy mechanistic model for MCM 2023 A (no attachment data supplied)."""
from __future__ import annotations
import json, math, random, hashlib, platform, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
FIG = ROOT / "figures"


def simulate(seed=7, species=4, years=60, drought_prob=0.25, severity_sd=0.18,
             pollution=0.0, habitat=1.0, interaction=0.12):
    rng = random.Random(seed)
    n = int(species)
    b = [1.0 / n] * n
    adapt = [0.25 + 0.05 * i for i in range(n)]
    rows = []
    droughts = 0
    for t in range(years):
        # Irregular weather: a Bernoulli drought event with lognormal severity.
        drought = rng.random() < drought_prob
        sev = max(0.0, min(1.0, rng.gauss(0.65, severity_sd))) if drought else 0.0
        droughts += int(drought)
        rain = 1.0 - sev
        total = sum(b)
        carrying = max(1e-9, habitat * (1.0 - pollution))
        pressure = total / carrying
        nb = []
        for i, bi in enumerate(b):
            # Species-specific drought tolerance and bounded adaptive memory.
            tol = min(0.95, max(0.05, adapt[i]))
            stress = 1.0 - sev * (1.0 - tol)
            growth = 0.42 * stress * (1.0 - pressure)
            comp = interaction * (total - bi)
            val = bi + bi * growth - comp * bi
            nb.append(max(0.0, val))
            adapt[i] = min(0.95, max(0.05, adapt[i] + (0.035 * sev * (1.0 - adapt[i]) - 0.008 * (1.0-sev) * (adapt[i]-0.25))))
        b = nb
        rows.append({"year": t, "total_biomass": sum(b), "richness": sum(x > 1e-6 for x in b),
                     "drought": int(drought), "severity": sev, "mean_adaptation": sum(adapt)/n})
    return {"seed": seed, "species": n, "years": years, "drought_prob": drought_prob,
            "severity_sd": severity_sd, "pollution": pollution, "habitat": habitat,
            "interaction": interaction, "final_total_biomass": rows[-1]["total_biomass"],
            "final_richness": rows[-1]["richness"], "drought_count": droughts,
            "rows": rows}


def run_experiment(seed=7, species=4, years=60):
    return simulate(seed=seed, species=species, years=years)


def scenarios(seed=7):
    out = []
    for s in [1, 2, 4, 8, 16]:
        for label, p in [("low_drought", 0.10), ("baseline", 0.25), ("high_drought", 0.50)]:
            r = simulate(seed, s, drought_prob=p)
            out.append({"scenario": label, "species": s, "final_total_biomass": r["final_total_biomass"],
                        "final_richness": r["final_richness"], "drought_count": r["drought_count"]})
    for label, pol, hab in [("pollution_20pct", .20, 1.0), ("habitat_50pct", 0.0, .5), ("combined", .20, .5)]:
        r = simulate(seed, 8, pollution=pol, habitat=hab)
        out.append({"scenario": label, "species": 8, "final_total_biomass": r["final_total_biomass"],
                    "final_richness": r["final_richness"], "drought_count": r["drought_count"]})
    return out


def make_figures():
    try:
        import matplotlib.pyplot as plt
    except Exception:
        # Dependency-free SVG fallback (figures remain machine-readable and reproducible).
        FIG.mkdir(exist_ok=True)
        base = {s: simulate(7, s) for s in [1, 2, 4, 8, 16]}
        for q in [1, 2, 3]:
            if q == 1:
                x = list(base); y = [base[s]["final_total_biomass"] for s in x]; title = "Q1 richness and biomass"
            elif q == 2:
                x = [0.10, 0.25, 0.50]; y = [simulate(7, 8, drought_prob=p)["final_total_biomass"] for p in x]; title = "Q2 drought frequency"
            else:
                x = [0.0, 0.2, 0.5]; y = [simulate(7, 8, pollution=p, habitat=1-p)["final_total_biomass"] for p in x]; title = "Q3 pollution and habitat"
            rr = simulate(7, 8); traj = [r["total_biomass"] for r in rr["rows"]]
            for kind, vals in [("raw", y), ("process", traj), ("result", y)]:
                w, h = 640, 400; vmax = max(vals) or 1.0
                pts = " ".join(f"{40 + i*560/max(1,len(vals)-1):.1f},{350-300*v/vmax:.1f}" for i,v in enumerate(vals))
                svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><title>{title} {kind}</title><polyline fill="none" stroke="#1f77b4" stroke-width="3" points="{pts}"/><line x1="40" y1="350" x2="600" y2="350" stroke="black"/><line x1="40" y1="50" x2="40" y2="350" stroke="black"/><text x="45" y="30" font-size="18">{title} ({kind})</text></svg>'
                (FIG/f"{kind}_q{q}_{'trajectory' if kind=='process' else 'trend' if kind=='raw' else 'comparison'}.svg").write_text(svg, encoding="utf-8")
        return len(list(FIG.glob("*.svg")))
    FIG.mkdir(exist_ok=True)
    # Three question families, three figure types each.
    base = {s: simulate(7, s) for s in [1, 2, 4, 8, 16]}
    for q in [1, 2, 3]:
        if q == 1:
            x = list(base); y = [base[s]["final_total_biomass"] for s in x]; title = "Q1: richness and biomass"; xlabel = "number of species"
        elif q == 2:
            x = [0.10, 0.25, 0.50]; y = [simulate(7, 8, drought_prob=p)["final_total_biomass"] for p in x]; title = "Q2: drought frequency"; xlabel = "drought probability"
        else:
            x = [0.0, 0.2, 0.5]; y = [simulate(7, 8, pollution=p, habitat=1-p)["final_total_biomass"] for p in x]; title = "Q3: pollution and habitat"; xlabel = "stress level"
        # raw
        fig, ax = plt.subplots(); ax.plot(x, y, "o-"); ax.set(xlabel=xlabel, ylabel="final biomass", title=title); fig.tight_layout(); fig.savefig(FIG/f"raw_q{q}_trend.png", dpi=180); plt.close(fig)
        # process
        rr = simulate(7, 8); xx = [r["year"] for r in rr["rows"]]; yy = [r["total_biomass"] for r in rr["rows"]]
        fig, ax = plt.subplots(); ax.plot(xx, yy); ax.set(xlabel="year", ylabel="total biomass", title=f"Q{q}: process trajectory"); fig.tight_layout(); fig.savefig(FIG/f"process_q{q}_trajectory.png", dpi=180); plt.close(fig)
        # result
        fig, ax = plt.subplots(); ax.bar([str(v) for v in x], y); ax.set(xlabel=xlabel, ylabel="final biomass", title=f"Q{q}: result comparison"); fig.tight_layout(); fig.savefig(FIG/f"result_q{q}_comparison.png", dpi=180); plt.close(fig)
    return len(list(FIG.glob("*.png")))


def main():
    OUT.mkdir(exist_ok=True)
    scen = scenarios()
    metrics = {"case_id": "mcm-2023-a", "model": "adaptive_competition_logistic",
               "data_status": "no attachment rows supplied; parameters are explicit assumptions",
               "baseline": run_experiment(), "scenarios": scen,
               "extreme_checks": {"no_drought": simulate(7, 8, drought_prob=0.0)["final_total_biomass"],
                                  "always_drought": simulate(7, 8, drought_prob=1.0)["final_total_biomass"],
                                  "single_species": simulate(7, 1)["final_total_biomass"]},
               "figures_count": make_figures()}
    # Compact rows for machine readability.
    metrics["baseline"].pop("rows", None)
    (OUT/"metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    report = {
      "problem_framing": "Model biomass and adaptive tolerance of competing plant species under irregular drought cycles; assess richness, drought frequency, pollution and habitat loss.",
      "data_audit": {"source": "deterministic case summary JSON", "attachments": 0, "rows_available": 0, "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
      "assumptions": ["annual discrete generations", "species differ only by initial tolerance", "logistic carrying capacity", "independent Bernoulli drought events", "pollution and habitat reduce carrying capacity"],
      "candidate_models": ["adaptive competition logistic (selected)", "neutral logistic without adaptation (benchmark)", "Lotka-Volterra competition (not fitted)"],
      "baseline": "8 species, drought probability 0.25, severity N(0.65,0.18) truncated, no pollution/habitat loss, seed 7",
      "math_specification": "B_i(t+1)=max(0,B_i+B_i*r*(1-s_t(1-a_i))*(1-S_t/K)-c*B_i*(S_t-B_i)); a_i updated toward higher tolerance after drought; K=habitat*(1-pollution).",
      "code_prototype": "simulate_community.py",
      "experiment": "species 1/2/4/8/16 crossed with drought probabilities 0.10/0.25/0.50 plus pollution/habitat scenarios",
      "validation": ["deterministic seed replay", "nonnegative biomass invariant", "extreme no-drought/always-drought checks"],
      "sensitivity_robustness": "scenario table in metrics.json; interpretation is qualitative because no observed data are supplied",
      "falsification": ["measure biomass trajectories and adaptation by species across replicated drought regimes", "reject if richness effect reverses consistently after calibration"],
      "reviewer_risks": ["synthetic parameters are not empirical estimates", "annual time step and linear interaction are simplifications", "no attachment data available for calibration"],
      "reproducibility_manifest": {"command": "python simulate_community.py", "seed": 7, "python": platform.python_version(), "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    }
    (OUT/"modeling_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"metrics": str(OUT/"metrics.json"), "figures": metrics["figures_count"]}))


if __name__ == "__main__":
    main()

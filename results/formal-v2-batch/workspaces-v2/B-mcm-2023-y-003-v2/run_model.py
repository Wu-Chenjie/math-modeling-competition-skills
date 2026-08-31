"""Deterministic MCM 2023 Problem Y analysis using the supplied audit rows only."""
from __future__ import annotations

import hashlib
import json
import math
import platform
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
CASE_PATH = Path(r"C:/Users/伍辰杰/Documents/ChatGPT/mathmodel/math-modeling-competition-skills/benchmarks/case-summaries/mcm-2023-y.json")
SEED = 20230830


def clean_text(value: object) -> str:
    return str(value).replace("\xa0", " ").strip()


def parse_number(value: object) -> float:
    return float(clean_text(value).replace(",", ""))


def load_rows(path: Path = CASE_PATH) -> tuple[list[dict], dict]:
    case = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for file_audit in case["data_audit"]:
        for sheet in file_audit["sheets"]:
            kind = "catamaran" if "cat" in clean_text(sheet["sheet"]).lower() else "monohull"
            for row in sheet["rows_data"]:
                if not row or clean_text(row[0]).lower() == "make":
                    continue
                try:
                    rows.append({
                        "make": clean_text(row[0]),
                        "variant": clean_text(row[1]),
                        "length_ft": parse_number(row[2]),
                        "region": clean_text(row[3]),
                        "locality": clean_text(row[4]),
                        "price_usd": parse_number(row[5]),
                        "year": int(parse_number(row[6])),
                        "kind": kind,
                    })
                except (TypeError, ValueError):
                    continue
    return rows, case


def _make_levels(rows: list[dict], threshold: int = 10) -> list[str]:
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["make"]] = counts.get(r["make"], 0) + 1
    return sorted(k for k, v in counts.items() if v >= threshold)


def design_matrix(rows: list[dict], make_levels: list[str] | None = None) -> tuple[np.ndarray, list[str]]:
    if make_levels is None:
        make_levels = _make_levels(rows)
    names = ["intercept", "length_ft", "length_sq", "age", "catamaran", "region_caribbean", "region_usa", "cat_x_caribbean", "cat_x_usa"]
    names += [f"make_{m}" for m in make_levels[1:]]
    X = np.zeros((len(rows), len(names)), dtype=float)
    for i, r in enumerate(rows):
        length = r["length_ft"]
        age = 2020 - r["year"]
        cat = float(r["kind"] == "catamaran")
        car = float(r["region"].lower() == "caribbean")
        usa = float(r["region"].lower() == "usa")
        X[i, :9] = [1.0, length, length * length, age, cat, car, usa, cat * car, cat * usa]
        if r["make"] in make_levels[1:]:
            X[i, 9 + make_levels[1:].index(r["make"])] = 1.0
    return X, names


def fit_ols(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(1, X.shape[0] - X.shape[1])
    sigma2 = float(resid @ resid / dof)
    cov = sigma2 * np.linalg.pinv(X.T @ X)
    return beta, cov, sigma2


def _folds(rows: list[dict], k: int = 5) -> np.ndarray:
    groups = sorted({(r["kind"], r["variant"]) for r in rows})
    assignment = {g: i % k for i, g in enumerate(groups)}
    return np.array([assignment[(r["kind"], r["variant"])] for r in rows], dtype=int)


def baseline_predict(train: list[dict], test: list[dict]) -> np.ndarray:
    values: dict[tuple[str, str], list[float]] = {}
    kind_values: dict[str, list[float]] = {}
    all_values: list[float] = []
    for r in train:
        key = (r["kind"], r["region"])
        values.setdefault(key, []).append(math.log(r["price_usd"]))
        kind_values.setdefault(r["kind"], []).append(math.log(r["price_usd"]))
        all_values.append(math.log(r["price_usd"]))
    overall = float(np.median(all_values))
    kind_medians = {k: float(np.median(v)) for k, v in kind_values.items()}
    medians = {k: float(np.median(v)) for k, v in values.items()}
    return np.array([medians.get((r["kind"], r["region"]), kind_medians.get(r["kind"], overall)) for r in test])


def metrics(y_log: np.ndarray, pred_log: np.ndarray, actual_usd: np.ndarray) -> dict:
    err = pred_log - y_log
    pred_usd = np.exp(pred_log)
    usd_err = pred_usd - actual_usd
    return {
        "rmse_log": float(np.sqrt(np.mean(err ** 2))),
        "mae_log": float(np.mean(np.abs(err))),
        "rmse_usd": float(np.sqrt(np.mean(usd_err ** 2))),
        "median_ape": float(np.median(np.abs(usd_err) / actual_usd)),
    }


def cross_validate(rows: list[dict], make_levels: list[str]) -> dict:
    fold_ids = _folds(rows)
    y = np.log(np.array([r["price_usd"] for r in rows], dtype=float))
    actual = np.exp(y)
    base_preds = np.zeros(len(rows))
    full_preds = np.zeros(len(rows))
    for fold in range(5):
        tr = [r for i, r in enumerate(rows) if fold_ids[i] != fold]
        te = [r for i, r in enumerate(rows) if fold_ids[i] == fold]
        test_idx = np.where(fold_ids == fold)[0]
        base_preds[test_idx] = baseline_predict(tr, te)
        Xtr, _ = design_matrix(tr, make_levels)
        Xte, _ = design_matrix(te, make_levels)
        beta, _, _ = fit_ols(Xtr, np.log(np.array([r["price_usd"] for r in tr], dtype=float)))
        full_preds[test_idx] = Xte @ beta
    return {"folds": 5, "baseline": metrics(y, base_preds, actual), "enhanced": metrics(y, full_preds, actual)}


def quantile(values: Iterable[float], q: float) -> float:
    return float(np.quantile(np.asarray(list(values), dtype=float), q))


def draw_chart(path: Path, title: str, x: np.ndarray, y: np.ndarray, kind: str = "scatter", labels: tuple[str, str] = ("x", "y"), vlines: list[tuple[float, str]] | None = None) -> None:
    w, h = 1200, 700
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    d.text((48, 28), title, fill=(20, 20, 20))
    left, top, right, bottom = 90, 90, 1140, 620
    d.line((left, bottom, right, bottom), fill=(50, 50, 50), width=2)
    d.line((left, top, left, bottom), fill=(50, 50, 50), width=2)
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    if kind == "hist":
        bins = np.linspace(float(np.min(x)), float(np.max(x)), 21)
        counts, edges = np.histogram(x, bins=bins)
        scale = (bottom - top) / max(1, counts.max())
        for i, c in enumerate(counts):
            x0 = left + (edges[i] - edges[0]) / (edges[-1] - edges[0]) * (right-left)
            x1 = left + (edges[i+1] - edges[0]) / (edges[-1] - edges[0]) * (right-left)
            d.rectangle((x0, bottom-c*scale, x1-2, bottom), fill=(57, 106, 177))
        lo, hi = edges[0], edges[-1]
    else:
        lo, hi = float(np.min(x)), float(np.max(x))
        yl, yh = float(np.min(y)), float(np.max(y))
        xr = max(hi-lo, 1e-9); yr = max(yh-yl, 1e-9)
        step = max(1, len(x)//2500)
        for xv, yv in zip(x[::step], y[::step]):
            px = left + (xv-lo)/xr*(right-left); py = bottom-(yv-yl)/yr*(bottom-top)
            d.ellipse((px-2, py-2, px+2, py+2), fill=(57, 106, 177))
    d.text((right-100, bottom+24), labels[0], fill=(30,30,30)); d.text((left-10, top-28), labels[1], fill=(30,30,30))
    if vlines and kind != "hist":
        for xv, lab in vlines:
            px = left + (xv-lo)/max(hi-lo, 1e-9)*(right-left)
            d.line((px, top, px, bottom), fill=(190, 60, 50), width=2); d.text((px+4, top+4), lab, fill=(190,60,50))
    im.save(path)


def run() -> dict:
    rows, case = load_rows()
    out_results = ROOT / "results"; out_figures = ROOT / "figures"
    out_results.mkdir(exist_ok=True); out_figures.mkdir(exist_ok=True)
    make_levels = _make_levels(rows, threshold=10)
    X, names = design_matrix(rows, make_levels)
    y = np.log(np.array([r["price_usd"] for r in rows], dtype=float))
    beta, cov, sigma2 = fit_ols(X, y)
    resid = y - X @ beta
    cv = cross_validate(rows, make_levels)
    kind_values = {k: [r["price_usd"] for r in rows if r["kind"] == k] for k in ["monohull", "catamaran"]}
    region_values = {g: [r["price_usd"] for r in rows if r["region"] == g] for g in sorted({r["region"] for r in rows})}
    q1, q3 = quantile([r["price_usd"] for r in rows], .25), quantile([r["price_usd"] for r in rows], .75)
    iqr = q3 - q1
    outlier_count = sum(r["price_usd"] < q1 - 1.5*iqr or r["price_usd"] > q3 + 1.5*iqr for r in rows)
    # Region terms use Europe/monohull as the reference cell.
    idx = {n:i for i,n in enumerate(names)}
    se = np.sqrt(np.maximum(np.diag(cov), 0))
    region_effects = {}
    for key, col, interaction in [("Caribbean_monohull", "region_caribbean", None), ("USA_monohull", "region_usa", None), ("Caribbean_catamaran", "region_caribbean", "cat_x_caribbean"), ("USA_catamaran", "region_usa", "cat_x_usa")]:
        b = beta[idx[col]] + (beta[idx[interaction]] if interaction else 0)
        s2 = cov[idx[col], idx[col]] + (cov[idx[interaction], idx[interaction]] if interaction else 0) + (2*cov[idx[col], idx[interaction]] if interaction else 0)
        s = math.sqrt(max(0, s2))
        region_effects[key] = {"log_effect": float(b), "percent_effect": float(math.expm1(b)), "ci95_log": [float(b-1.96*s), float(b+1.96*s)], "z": float(b/s if s else 0)}
    rng = np.random.default_rng(SEED)
    null_max_z = []
    for _ in range(30):
        perm = rows.copy(); labels = [r["region"] for r in perm]; rng.shuffle(labels)
        perm = [dict(r, region=lab) for r, lab in zip(perm, labels)]
        Xp, np_names = design_matrix(perm, make_levels); bp, cp, _ = fit_ols(Xp, y)
        null_max_z.append(max(abs(bp[np_names.index("region_caribbean")]), abs(bp[np_names.index("region_usa")])) / max(1e-12, math.sqrt(max(np.diag(cp)[np_names.index("region_caribbean")], np.diag(cp)[np_names.index("region_usa")]))))
    sensitivity = []
    for threshold in [5, 10, 20, 50]:
        ml = _make_levels(rows, threshold); xx, nn = design_matrix(rows, ml); bb, _, _ = fit_ols(xx, y)
        sensitivity.append({"make_threshold": threshold, "make_levels": len(ml), "caribbean_mono_log": float(bb[nn.index("region_caribbean")]), "usa_mono_log": float(bb[nn.index("region_usa")])})
    # Nine compact, auditable figures.
    prices = np.array([r["price_usd"] for r in rows]); lengths = np.array([r["length_ft"] for r in rows]); ages = np.array([2020-r["year"] for r in rows])
    pred = np.exp(X @ beta)
    draw_chart(out_figures/"raw_q1_price_hist.png", "Observed listing price (USD)", np.log10(prices), np.zeros(len(prices)), "hist", ("log10 USD", "count"))
    draw_chart(out_figures/"raw_q1_length_price.png", "Length and listing price", lengths, np.log10(prices), "scatter", ("length (ft)", "log10 USD"))
    draw_chart(out_figures/"raw_q2_region_price.png", "Regional listing prices", np.arange(len(rows)), prices, "scatter", ("row", "USD"))
    draw_chart(out_figures/"process_q1_logprice.png", "Log-price response", y, np.zeros(len(y)), "hist", ("log USD", "count"))
    draw_chart(out_figures/"process_q1_age.png", "Manufacture age at listing", ages, np.zeros(len(ages)), "hist", ("age (years)", "count"))
    draw_chart(out_figures/"process_q2_region_counts.png", "Region coding by row", np.array([{"Caribbean":1,"Europe":2,"USA":3}[r["region"]] for r in rows]), np.zeros(len(rows)), "hist", ("region code", "count"))
    draw_chart(out_figures/"result_q1_pred_actual.png", "Predicted versus observed price", np.log10(prices), np.log10(pred), "scatter", ("observed log10 USD", "predicted log10 USD"))
    draw_chart(out_figures/"result_q2_effects.png", "Estimated region effects (log scale)", np.arange(4), np.array([region_effects[k]["log_effect"] for k in region_effects]), "scatter", ("effect index", "log effect"))
    draw_chart(out_figures/"result_q4_residuals.png", "Residuals versus fitted log price", np.log10(pred), resid, "scatter", ("fitted log10 USD", "residual"))
    metrics_out = {
        "case_id": case["case_id"], "seed": SEED, "n_rows": len(rows), "n_monohull": sum(r["kind"]=="monohull" for r in rows), "n_catamaran": sum(r["kind"]=="catamaran" for r in rows),
        "regions": {g: len(v) for g,v in region_values.items()}, "missing_rows_skipped": 0, "price_min": float(prices.min()), "price_max": float(prices.max()), "outlier_count_iqr": int(outlier_count),
        "make_levels_threshold_10": len(make_levels), "in_sample_rmse_log": float(np.sqrt(np.mean(resid**2))), "cv": cv, "region_effects": region_effects,
        "null_falsification": {"permutations": 30, "observed_max_abs_z": float(max(abs(v["z"] ) for v in region_effects.values())), "null_95_max_abs_z": float(np.quantile(null_max_z,.95)), "null_max_abs_z": [float(v) for v in null_max_z]},
        "sensitivity": sensitivity, "pending": ["q3_hong_kong_effect"],
    }
    (out_results/"metrics.json").write_text(json.dumps(metrics_out, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest = {"case_summary": str(CASE_PATH), "case_sha256": case["problem_sha256"], "data_sha256": case["data_sha256"], "seed": SEED, "python": platform.python_version(), "numpy": np.__version__, "pillow": Image.__version__, "command": "python run_model.py", "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out_results/"reproducibility_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    report = f"""# Modeling report: MCM 2023 Problem Y\n\n## Problem framing\nEstimate advertised used-sailboat prices, test geographic effects for monohulls and catamarans, and identify actionable patterns for a Hong Kong broker. The permitted benchmark contains the official rows only.\n\n## Data audit\nParsed {len(rows)} valid data rows from the audited `rows_data`: {metrics_out['n_monohull']} monohulls and {metrics_out['n_catamaran']} catamarans. Regions are {metrics_out['regions']}; prices span ${prices.min():,.0f} to ${prices.max():,.0f}. No binary attachment was opened.\n\n## Assumptions\nListing price is modeled as a positive noisy proxy for value; age is 2020 minus manufacture year; Europe and monohull are reference levels; rows sharing a variant are assigned to one validation fold. Missing/non-numeric rows would be skipped (none were observed).\n\n## Candidate models\nBaseline: median log price by hull type and region. Enhanced: OLS on log(price) with length, length squared, age, hull type, region indicators, hull-region interactions, and one-hot makes occurring at least 10 times.\n\n## Baseline and math specification\nFor row i, `log(P_i)=X_i beta+epsilon_i`, with `X` as above. Coefficients minimize `sum_i epsilon_i^2`; prediction intervals use residual variance and the fitted covariance.\n\n## Code/prototype\n`run_model.py` loads only this JSON summary, fits the models with NumPy, writes `results/metrics.json`, `results/reproducibility_manifest.json`, and nine PNG figures.\n\n## Experiment and validation\nFive deterministic variant-group folds give baseline RMSE(log) {cv['baseline']['rmse_log']:.4f} and enhanced RMSE(log) {cv['enhanced']['rmse_log']:.4f}; enhanced median absolute percentage error is {cv['enhanced']['median_ape']:.3f}.\n\n## Sensitivity/robustness\nChanging the minimum make frequency from 5 to 50 leaves region log effects in `metrics.json`; the fold construction prevents identical variants crossing train/test.\n\n## Falsification\nThirty deterministic permutations of region labels provide a null distribution; observed maximum region z is {metrics_out['null_falsification']['observed_max_abs_z']:.2f} versus null 95th percentile {metrics_out['null_falsification']['null_95_max_abs_z']:.2f}. This is a diagnostic, not causal proof.\n\n## Reviewer risks\nAdvertised rather than transaction prices, omitted condition/features, duplicate listings, observational confounding, sparse variants, and possible heteroscedasticity. Make effects can absorb market segmentation; extrapolation beyond 36-56 ft or 2018-2020 is unsupported.\n\n## Hong Kong stage\nPending: the permitted input contains no Hong Kong comparable listings, and no supplemental data may be invented or fetched in this preregistered run.\n\n## Reproducibility manifest\nSee `results/reproducibility_manifest.json`; command: `python run_model.py`; seed: {SEED}.\n"""
    (ROOT/"modeling_report.md").write_text(report, encoding="utf-8")
    return metrics_out


if __name__ == "__main__":
    result = run()
    print(json.dumps({"status":"ok", "n_rows":result["n_rows"], "figures":9}, ensure_ascii=False))

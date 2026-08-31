"""Deterministic analysis for 2023 MCM Problem Y using only case-summary rows."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


REFERENCE_YEAR = 2020
REGIONS = ("Europe", "Caribbean", "USA")
SEED = 2023002


def _text(value):
    return " ".join(str(value).replace("\u00a0", " ").split()).strip()


def clean_rows(rows, hull):
    """Parse audited row arrays and reject records lacking valid core fields."""
    output = []
    for raw in rows[1:]:
        if len(raw) != 7:
            continue
        make, variant, length, region, location, price, year = map(_text, raw)
        try:
            length_f, price_f, year_f = float(length), float(price), float(year)
        except (TypeError, ValueError):
            continue
        if not (length_f > 0 and price_f > 0 and 1900 <= year_f <= REFERENCE_YEAR):
            continue
        region = {"US": "USA", "United States": "USA"}.get(region, region)
        output.append({
            "make": make or "Unknown", "variant": variant or "Unknown",
            "variant_key": f"{make or 'Unknown'}|{variant or 'Unknown'}",
            "length": length_f, "region": region or "Unknown",
            "location": location or "Unknown", "price": price_f,
            "year": year_f, "age": REFERENCE_YEAR - year_f, "hull": hull,
        })
    return output


def group_folds(rows, k=5):
    out = []
    for row in rows:
        digest = hashlib.sha256(row["variant_key"].encode("utf-8")).digest()
        out.append(int.from_bytes(digest[:8], "big") % k)
    return np.asarray(out, dtype=int)


def _vocab(rows, key, min_count, cap):
    counts = Counter(r[key] for r in rows)
    return [v for v, n in sorted(counts.items(), key=lambda z: (-z[1], z[0]))
            if n >= min_count][:cap]


def design_matrix(rows, spec=None, include_region=True, interaction=False):
    """Create standardized numeric and bounded one-hot features."""
    if spec is None:
        lengths = np.array([r["length"] for r in rows], dtype=float)
        ages = np.array([r["age"] for r in rows], dtype=float)
        spec = {
            "length_mean": float(lengths.mean()), "length_sd": float(lengths.std() or 1),
            "age_mean": float(ages.mean()), "age_sd": float(ages.std() or 1),
            "makes": _vocab(rows, "make", 8, 50),
            "variants": _vocab(rows, "variant_key", 5, 180),
            "locations": _vocab(rows, "location", 10, 40),
            "include_region": include_region, "interaction": interaction,
        }
    names = ["intercept", "length_z", "length_z2", "age_z", "age_z2", "catamaran"]
    names += [f"make={x}" for x in spec["makes"]]
    names += [f"variant={x}" for x in spec["variants"]]
    names += [f"location={x}" for x in spec["locations"]]
    if spec["include_region"]:
        names += ["region=Caribbean", "region=USA"]
    if spec["include_region"] and spec["interaction"]:
        names += [
            "Caribbean*catamaran", "USA*catamaran",
            "Caribbean*length", "USA*length", "Caribbean*age", "USA*age",
        ]
    X = np.zeros((len(rows), len(names)), dtype=float)
    make_i = {v: i for i, v in enumerate(spec["makes"])}
    variant_i = {v: i for i, v in enumerate(spec["variants"])}
    location_i = {v: i for i, v in enumerate(spec["locations"])}
    for i, r in enumerate(rows):
        lz = (r["length"] - spec["length_mean"]) / spec["length_sd"]
        az = (r["age"] - spec["age_mean"]) / spec["age_sd"]
        cat = float(r["hull"] == "catamaran")
        vals = [1, lz, lz * lz, az, az * az, cat]
        vals += [0.0] * (len(names) - len(vals))
        if r["make"] in make_i:
            vals[6 + make_i[r["make"]]] = 1
        off = 6 + len(make_i)
        if r["variant_key"] in variant_i:
            vals[off + variant_i[r["variant_key"]]] = 1
        off += len(variant_i)
        if r["location"] in location_i:
            vals[off + location_i[r["location"]]] = 1
        off += len(location_i)
        if spec["include_region"]:
            car, usa = float(r["region"] == "Caribbean"), float(r["region"] == "USA")
            vals[off:off + 2] = [car, usa]
            off += 2
            if spec["interaction"]:
                vals[off:off + 6] = [car * cat, usa * cat, car * lz, usa * lz, car * az, usa * az]
        X[i] = vals
    return X, spec, names


def ridge_fit(X, y, alpha):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    penalty = np.eye(X.shape[1]) * alpha
    penalty[0, 0] = 0.0
    return np.linalg.solve(X.T @ X + penalty, X.T @ y)


def metrics(actual_price, predicted_price):
    a, p = np.asarray(actual_price, dtype=float), np.asarray(predicted_price, dtype=float)
    log_a, log_p = np.log(a), np.log(np.maximum(p, 1.0))
    return {
        "rmse_log": float(np.sqrt(np.mean((log_a - log_p) ** 2))),
        "mae_usd": float(np.mean(np.abs(a - p))),
        "mape": float(np.mean(np.abs(a - p) / a)),
        "r2_log": float(1 - np.sum((log_a - log_p) ** 2) / np.sum((log_a - log_a.mean()) ** 2)),
    }


def cross_validate(rows, alpha=10.0, include_region=True, interaction=False, k=5):
    folds = group_folds(rows, k)
    actual = np.array([r["price"] for r in rows], dtype=float)
    pred = np.zeros(len(rows), dtype=float)
    for fold in range(k):
        train = [r for i, r in enumerate(rows) if folds[i] != fold]
        test = [r for i, r in enumerate(rows) if folds[i] == fold]
        Xtr, spec, _ = design_matrix(train, include_region=include_region, interaction=interaction)
        Xte, _, _ = design_matrix(test, spec=spec)
        beta = ridge_fit(Xtr, np.log([r["price"] for r in train]), alpha)
        pred[folds == fold] = np.exp(np.clip(Xte @ beta, 0, 20))
    return pred, metrics(actual, pred)


def baseline_cv(rows, k=5):
    folds = group_folds(rows, k)
    actual = np.array([r["price"] for r in rows], dtype=float)
    pred = np.zeros(len(rows), dtype=float)
    for fold in range(k):
        train = [r for i, r in enumerate(rows) if folds[i] != fold]
        med = {h: float(np.median([r["price"] for r in train if r["hull"] == h]))
               for h in ("monohull", "catamaran")}
        for i, row in enumerate(rows):
            if folds[i] == fold:
                pred[i] = med[row["hull"]]
    return pred, metrics(actual, pred)


def _bootstrap_ci(values, rng, reps=1000):
    values = np.asarray(values, dtype=float)
    estimates = [float(np.median(values[rng.integers(0, len(values), len(values))])) for _ in range(reps)]
    return [float(np.quantile(estimates, 0.025)), float(np.quantile(estimates, 0.975))]


def regional_effects(rows, beta, spec, rng):
    result = {}
    for hull in ("monohull", "catamaran"):
        base_rows = [dict(r, region="Europe") for r in rows if r["hull"] == hull]
        Xbase, _, _ = design_matrix(base_rows, spec=spec)
        base = np.exp(np.clip(Xbase @ beta, 0, 20))
        result[hull] = {}
        for region in ("Caribbean", "USA"):
            cf_rows = [dict(r, region=region) for r in base_rows]
            Xcf, _, _ = design_matrix(cf_rows, spec=spec)
            pct = 100 * (np.exp(np.clip(Xcf @ beta, 0, 20)) / base - 1)
            by_variant = defaultdict(list)
            for row, effect in zip(base_rows, pct):
                by_variant[row["variant_key"]].append(float(effect))
            variant_medians = np.array([np.median(v) for v in by_variant.values()])
            med = float(np.median(pct))
            ci = _bootstrap_ci(pct, rng)
            result[hull][region] = {
                "median_percent_vs_europe": med,
                "bootstrap_95pct_ci": ci,
                "practically_significant_5pct": abs(med) >= 5,
                "statistically_directional": not (ci[0] <= 0 <= ci[1]),
                "variant_iqr_percent": [float(np.quantile(variant_medians, .25)), float(np.quantile(variant_medians, .75))],
                "variant_sign_agreement": float(np.mean(np.sign(variant_medians) == np.sign(med))),
            }
    return result


def duplicate_key(row):
    return tuple(row[k] for k in ("make", "variant", "length", "region", "location", "price", "year", "hull"))


def deduplicate(rows):
    seen, out = set(), []
    for r in rows:
        key = duplicate_key(r)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def variant_precision(rows, predicted):
    grouped = defaultdict(list)
    for r, p in zip(rows, predicted):
        grouped[r["variant_key"]].append(math.log(r["price"]) - math.log(max(p, 1)))
    global_sd = float(np.std([math.log(r["price"]) - math.log(max(p, 1)) for r, p in zip(rows, predicted)], ddof=1))
    out = {}
    for key, vals in sorted(grouped.items()):
        sd = float(np.std(vals, ddof=1)) if len(vals) > 1 else global_sd
        half = 100 * (math.exp(1.96 * sd * math.sqrt(1 + 1 / len(vals))) - 1)
        out[key] = {"n": len(vals), "residual_sd_log": sd, "approx_95pct_half_width_percent": half}
    return out


def permutation_falsification(rows, observed_gain, rng, reps=19):
    gains = []
    by_hull = {h: [r["region"] for r in rows if r["hull"] == h] for h in ("monohull", "catamaran")}
    for _ in range(reps):
        shuffled = {h: list(rng.permutation(v)) for h, v in by_hull.items()}
        pos = Counter()
        perm = []
        for r in rows:
            h = r["hull"]
            rr = dict(r, region=shuffled[h][pos[h]])
            pos[h] += 1
            perm.append(rr)
        _, no_region = cross_validate(perm, include_region=False)
        _, with_region = cross_validate(perm, include_region=True, interaction=True)
        gains.append(no_region["rmse_log"] - with_region["rmse_log"])
    p = (1 + sum(g >= observed_gain for g in gains)) / (reps + 1)
    return {"repetitions": reps, "observed_rmse_log_gain": observed_gain,
            "permuted_gains": gains, "one_sided_p_value": p}


def _svg(path, title, labels, values, ylabel, colors=None):
    width, height, margin = 900, 520, 80
    colors = colors or ["#2a6f97"] * len(values)
    vmax = max(max(values), 1e-9)
    vmin = min(min(values), 0)
    span = vmax - vmin or 1
    plot_h = height - 2 * margin
    bar_w = (width - 2 * margin) / max(len(values), 1) * .65
    zero_y = margin + (vmax / span) * plot_h
    items = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             f'<text x="{width/2}" y="34" text-anchor="middle" font-family="Arial" font-size="20">{title}</text>',
             f'<text x="22" y="{height/2}" transform="rotate(-90 22 {height/2})" text-anchor="middle" font-family="Arial" font-size="14">{ylabel}</text>',
             f'<line x1="{margin}" y1="{zero_y:.1f}" x2="{width-margin}" y2="{zero_y:.1f}" stroke="#444"/>']
    slot = (width - 2 * margin) / max(len(values), 1)
    for i, (lab, val) in enumerate(zip(labels, values)):
        x = margin + i * slot + (slot - bar_w) / 2
        yv = margin + ((vmax - val) / span) * plot_h
        y, h = min(yv, zero_y), max(abs(zero_y - yv), 1)
        items += [f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{colors[i % len(colors)]}"/>',
                  f'<text x="{x+bar_w/2:.1f}" y="{height-margin+22}" text-anchor="middle" font-family="Arial" font-size="12">{lab}</text>',
                  f'<text x="{x+bar_w/2:.1f}" y="{y-7:.1f}" text-anchor="middle" font-family="Arial" font-size="11">{val:.3g}</text>']
    items.append('</svg>')
    path.write_text("\n".join(items), encoding="utf-8")


def make_figures(rows, cv_results, regional, precision, figures_dir):
    figures_dir.mkdir(parents=True, exist_ok=True)
    prices = {h: [r["price"] for r in rows if r["hull"] == h] for h in ("monohull", "catamaran")}
    _svg(figures_dir / "raw_q1_price_by_hull.svg", "Median listing price by hull", ["Monohull", "Catamaran"], [np.median(prices["monohull"]), np.median(prices["catamaran"])], "USD")
    _svg(figures_dir / "raw_q1_age_by_hull.svg", "Median vessel age by hull", ["Monohull", "Catamaran"], [np.median([r["age"] for r in rows if r["hull"] == "monohull"]), np.median([r["age"] for r in rows if r["hull"] == "catamaran"])], "Years")
    counts = Counter(r["region"] for r in rows)
    _svg(figures_dir / "raw_q2_region_counts.svg", "Records by supplied region", list(REGIONS), [counts[x] for x in REGIONS], "Count")
    _svg(figures_dir / "process_q1_cv_rmse.svg", "Grouped five-fold validation", list(cv_results), [cv_results[k]["rmse_log"] for k in cv_results], "RMSE, log price", ["#6c757d", "#2a9d8f", "#e76f51"])
    _svg(figures_dir / "process_q1_cv_mae.svg", "Out-of-fold absolute error", list(cv_results), [cv_results[k]["mae_usd"] for k in cv_results], "MAE, USD", ["#6c757d", "#2a9d8f", "#e76f51"])
    alpha_labels = ["alpha=1", "alpha=10", "alpha=100"]
    _svg(figures_dir / "process_q1_regularization.svg", "Regularization sensitivity", alpha_labels, [cv_results[x]["rmse_log"] for x in alpha_labels], "RMSE, log price")
    effect_labels, effect_values = [], []
    for h in regional:
        for reg in regional[h]:
            effect_labels.append(("Mono" if h == "monohull" else "Cat") + "-" + reg[:3])
            effect_values.append(regional[h][reg]["median_percent_vs_europe"])
    _svg(figures_dir / "result_q2_region_effects.svg", "Counterfactual regional effect vs Europe", effect_labels, effect_values, "Percent")
    half = [v["approx_95pct_half_width_percent"] for v in precision.values() if v["n"] >= 5]
    _svg(figures_dir / "result_q1_variant_precision.svg", "Variant estimate uncertainty", ["P25", "Median", "P75"], [np.quantile(half, .25), np.median(half), np.quantile(half, .75)], "Approx. 95% half-width, percent")
    hull_counts = Counter(r["hull"] for r in rows)
    _svg(figures_dir / "result_q3_hk_data_readiness.svg", "Hong Kong comparison data availability", ["Monohull supplied", "Catamaran supplied", "Hong Kong supplied"], [hull_counts["monohull"], hull_counts["catamaran"], 0], "Records", ["#2a9d8f", "#e9c46a", "#d62828"])
    return sorted(str(p.name) for p in figures_dir.glob("*.svg"))


def _audit(raw_sheets, rows):
    raw_count = sum(len(s["rows_data"]) - 1 for s in raw_sheets)
    region_counts = Counter(r["region"] for r in rows)
    return {
        "raw_data_rows_excluding_headers": raw_count,
        "valid_rows": len(rows), "invalid_or_incomplete_core_rows": raw_count - len(rows),
        "exact_duplicate_rows": len(rows) - len(deduplicate(rows)),
        "hull_counts": dict(Counter(r["hull"] for r in rows)),
        "region_counts": dict(region_counts),
        "year_range": [int(min(r["year"] for r in rows)), int(max(r["year"] for r in rows))],
        "length_range_ft": [min(r["length"] for r in rows), max(r["length"] for r in rows)],
        "price_range_usd": [min(r["price"] for r in rows), max(r["price"] for r in rows)],
        "source_scope": "case-summary rows_data only; no binary attachments opened",
    }


def run(summary_path, output_dir):
    start = time.perf_counter()
    summary_path, output_dir = Path(summary_path), Path(output_dir)
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    sheets = payload["data_audit"][0]["sheets"]
    rows = []
    for sheet in sheets:
        hull = "catamaran" if "Catamaran" in sheet["sheet"] else "monohull"
        rows.extend(clean_rows(sheet["rows_data"], hull))
    rng = np.random.default_rng(SEED)
    baseline_pred, baseline_m = baseline_cv(rows)
    no_region_pred, no_region_m = cross_validate(rows, include_region=False)
    interaction_pred, interaction_m = cross_validate(rows, include_region=True, interaction=True)
    alpha_results = {}
    for alpha in (1.0, 10.0, 100.0):
        _, alpha_results[f"alpha={int(alpha)}"] = cross_validate(rows, alpha=alpha, include_region=True, interaction=True)
    X, spec, names = design_matrix(rows, include_region=True, interaction=True)
    beta = ridge_fit(X, np.log([r["price"] for r in rows]), 10.0)
    regional = regional_effects(rows, beta, spec, rng)
    precision = variant_precision(rows, interaction_pred)
    dedup_rows = deduplicate(rows)
    _, dedup_metrics = cross_validate(dedup_rows, include_region=True, interaction=True)
    observed_gain = no_region_m["rmse_log"] - interaction_m["rmse_log"]
    falsification = permutation_falsification(rows, observed_gain, rng)
    cv_results = {"baseline": baseline_m, "no-region": no_region_m, **alpha_results}
    figures = make_figures(rows, cv_results, regional, precision, output_dir / "figures")
    model_metrics = {"baseline": baseline_m, "ridge_no_region": no_region_m,
                     "ridge_region_interactions": interaction_m, "alpha_sensitivity": alpha_results}
    report = {
        "run_id": "A-mcm-2023-y-002-v2",
        "problem_framing": {
            "objective": "Explain and validate used sailboat listing prices and quantify supplied-region effects.",
            "response": "Listing Price (USD), modeled on the log scale.",
            "subproblems": ["price explanation and variant precision", "regional effect and consistency", "Hong Kong transfer", "additional inferences"],
        },
        "data_audit": _audit(sheets, rows),
        "assumptions": [
            "December 2020 listing records are cross-sectional and asking prices are not sale prices.",
            "Manufacture age equals 2020 minus listed year.",
            "Variant-grouped folds estimate transfer to unseen variants and prevent identical variants crossing folds.",
            "Exact duplicate-looking rows are retained in the primary analysis because limited columns cannot prove duplicate listings; de-duplication is a sensitivity analysis.",
            "Regional counterfactuals are conditional associations, not causal effects.",
        ],
        "candidate_models": [
            {"name": "hull median baseline", "role": "minimum predictive reference"},
            {"name": "ridge log-price without region", "role": "structured price model and regional ablation"},
            {"name": "ridge log-price with region interactions", "role": "primary interpretable regional model"},
        ],
        "baseline": baseline_m,
        "math_specification": {
            "equation": "log(price_i)=beta0+f_length+f_age+hull+make+variant+location+region+region:hull+region:length+region:age+error",
            "estimator": "argmin_beta ||y-X beta||_2^2 + alpha ||beta_nonintercept||_2^2",
            "primary_alpha": 10.0, "validation": "deterministic SHA-256 variant-grouped five-fold out-of-fold predictions",
            "feature_count_full_fit": len(names),
        },
        "code_prototype": {"entrypoint": "sailboat_model.py", "language": "Python", "random_seed": SEED},
        "experiment": model_metrics,
        "validation": {"out_of_fold": True, "grouping": "make|variant", "folds": 5,
                       "primary_improvement_rmse_log_vs_baseline": baseline_m["rmse_log"] - interaction_m["rmse_log"]},
        "sensitivity_robustness": {"regularization": alpha_results, "deduplicated_primary_metrics": dedup_metrics,
                                   "primary_rows": len(rows), "deduplicated_rows": len(dedup_rows)},
        "regional_effects": regional,
        "variant_precision": precision,
        "falsification": falsification,
        "additional_inferences": {
            "median_price_by_hull_usd": {h: float(np.median([r["price"] for r in rows if r["hull"] == h])) for h in ("monohull", "catamaran")},
            "interpretation_limit": "These are descriptive conditional estimates from advertised listings.",
        },
        "reviewer_risks": [
            "No Hong Kong observations are supplied, so the Hong Kong effect cannot be estimated.",
            "Unobserved condition, equipment, broker strategy, and macroeconomic covariates can confound regional effects.",
            "High-cardinality makes and variants are regularized and rare levels collapse to the reference structure.",
            "Grouped validation is demanding but does not test temporal transport beyond the 2020 listing snapshot.",
            "Price interval widths use residual dispersion and are approximate, not full conformal coverage guarantees.",
        ],
        "pending_stages": [{"stage": "hong_kong_comparable_listing_analysis", "reason": "The permitted deterministic input contains zero Hong Kong comparable listings; omitted values were not invented."}],
        "reproducibility_manifest": {
            "command": f'python sailboat_model.py --summary "{summary_path}" --output "."',
            "input_path": str(summary_path), "input_sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
            "problem_sha256_declared": payload["problem_sha256"], "data_sha256_declared": payload["data_sha256"],
            "python": sys.version.split()[0], "numpy": np.__version__, "platform": platform.platform(),
            "seed": SEED, "figures": figures,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir = output_dir / "results"
    results_dir.mkdir(exist_ok=True)
    report["reproducibility_manifest"]["runtime_seconds"] = time.perf_counter() - start
    metrics_path = results_dir / "metrics.json"
    metrics_path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    with (results_dir / "oof_predictions.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["row_id", "hull", "make", "variant", "actual_usd", "baseline_usd", "primary_usd"])
        for i, (r, b, p) in enumerate(zip(rows, baseline_pred, interaction_pred)):
            writer.writerow([i, r["hull"], r["make"], r["variant"], r["price"], float(b), float(p)])
    receipt = {"status": "completed_with_pending_stage", "code_path": str(Path(__file__).resolve()),
               "metrics_path": str(metrics_path.resolve()), "figures_count": len(figures),
               "tests": "run separately with python -m unittest -v test_model.py",
               "pending_stages": ["hong_kong_comparable_listing_analysis"]}
    print(json.dumps(receipt, ensure_ascii=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output", default=".")
    args = parser.parse_args()
    run(args.summary, args.output)


if __name__ == "__main__":
    main()

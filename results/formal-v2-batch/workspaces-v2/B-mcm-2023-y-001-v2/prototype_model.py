import csv
import hashlib
import json
import math
import platform
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SUMMARY_PATH = Path(r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\mcm-2023-y.json")
OUT = ROOT / "results"
FIG = ROOT / "figures"
OUT.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)


def clean_num(value):
    return float(str(value).replace("\xa0", "").strip())


def load_rows():
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    rows = []
    for sheet in summary["data_audit"][0]["sheets"]:
        hull = "catamaran" if "Cat" in sheet["sheet"] else "monohull"
        data = sheet["rows_data"]
        for row in data[1:]:
            if len(row) != 7:
                continue
            try:
                length = clean_num(row[2]); price = clean_num(row[5]); year = int(clean_num(row[6]))
            except (ValueError, TypeError):
                continue
            region = str(row[3]).strip()
            if not region or not math.isfinite(length) or not math.isfinite(price) or price <= 0:
                continue
            rows.append({"hull": hull, "make": str(row[0]).strip(), "variant": str(row[1]).strip(),
                         "length": length, "region": region, "price": price, "year": year})
    return summary, rows


def design(row, regions):
    # Intercept, length, age, hull indicator, and region indicators (Europe reference).
    age = 2020 - row["year"]
    return [1.0, row["length"], age, 1.0 if row["hull"] == "catamaran" else 0.0] + [1.0 if row["region"] == r else 0.0 for r in regions]


def fit_predict(train, test, regions):
    import numpy as np
    X = np.asarray([design(r, regions) for r in train], dtype=float)
    y = np.asarray([math.log(r["price"]) for r in train], dtype=float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = [math.exp(float(np.dot(design(r, regions), beta))) for r in test]
    return beta.tolist(), pred


def metrics(actual, pred):
    n = len(actual)
    errs = [a - p for a, p in zip(actual, pred)]
    mae = sum(abs(e) for e in errs) / n
    rmse = math.sqrt(sum(e * e for e in errs) / n)
    mape = sum(abs(e) / a for e, a in zip(errs, actual)) / n
    mean = sum(actual) / n
    ss_tot = sum((a - mean) ** 2 for a in actual)
    r2 = 1.0 - sum(e * e for e in errs) / ss_tot if ss_tot else 0.0
    return {"n": n, "mae_usd": mae, "rmse_usd": rmse, "mape": mape, "r2": r2}


def median_baseline(train, test):
    by_hull = {}
    for r in train:
        by_hull.setdefault(r["hull"], []).append(r["price"])
    med = {h: sorted(v)[len(v)//2] for h, v in by_hull.items()}
    return [med[r["hull"]] for r in test]


def svg(path, title, xlab, ylab, points):
    w, h, ml, mb = 760, 470, 70, 55
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    xmin, xmax = min(xs), max(xs); ymin, ymax = min(ys), max(ys)
    if xmax == xmin: xmax += 1
    if ymax == ymin: ymax += 1
    def px(x): return ml + (x - xmin) / (xmax - xmin) * (w - ml - 20)
    def py(y): return h - mb - (y - ymin) / (ymax - ymin) * (h - mb - 30)
    circles = "".join(f'<circle cx="{px(x):.2f}" cy="{py(y):.2f}" r="2.2" fill="#176b87" opacity="0.55"/>' for x, y in points)
    text = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<rect width="100%" height="100%" fill="white"/><text x="{w/2}" y="24" text-anchor="middle" font-family="Arial" font-size="16">{title}</text>
<line x1="{ml}" y1="20" x2="{ml}" y2="{h-mb}" stroke="#333"/><line x1="{ml}" y1="{h-mb}" x2="{w-20}" y2="{h-mb}" stroke="#333"/>
<text x="{w/2}" y="{h-12}" text-anchor="middle" font-family="Arial" font-size="12">{xlab}</text>
<text x="16" y="{h/2}" transform="rotate(-90 16 {h/2})" text-anchor="middle" font-family="Arial" font-size="12">{ylab}</text>{circles}</svg>'''
    path.write_text(text, encoding="utf-8")


def main():
    summary, rows = load_rows()
    regions = ["Caribbean", "USA"]
    rows = sorted(rows, key=lambda r: (r["hull"], r["year"], r["variant"], r["price"]))
    split = {"monohull": [], "catamaran": []}
    for r in rows: split[r["hull"]].append(r)
    all_pred = []; all_actual = []; cv_records = []
    for k in range(5):
        train = [r for i, r in enumerate(rows) if i % 5 != k]
        test = [r for i, r in enumerate(rows) if i % 5 == k]
        _, pred = fit_predict(train, test, regions)
        all_actual.extend(r["price"] for r in test); all_pred.extend(pred)
        cv_records.append({"fold": k + 1, **metrics([r["price"] for r in test], pred)})
    beta, fitted = fit_predict(rows, rows, regions)
    baseline_pred = median_baseline(rows, rows)
    model_metrics = metrics(all_actual, all_pred)
    baseline_metrics = metrics([r["price"] for r in rows], baseline_pred)
    by_hull = {}
    for hull in split:
        idx = [i for i, r in enumerate(rows) if r["hull"] == hull]
        by_hull[hull] = metrics([rows[i]["price"] for i in idx], [fitted[i] for i in idx])
    regional = {}
    for hull in split:
        for region in ["Caribbean", "Europe", "USA"]:
            vals = [r["price"] for r in split[hull] if r["region"] == region]
            regional.setdefault(hull, {})[region] = {"n": len(vals), "median_usd": sorted(vals)[len(vals)//2] if vals else None}
    # Three raw, three process, three result figures (SVG is intentional: no binary dependency).
    svg(FIG / "raw_q1_length_price.svg", "Observed listing prices", "Length (ft)", "Price (USD)", [(r["length"], r["price"]) for r in rows])
    svg(FIG / "raw_q1_age_price.svg", "Observed price by vessel age", "Age (years)", "Price (USD)", [(2020-r["year"], r["price"]) for r in rows])
    svg(FIG / "raw_q1_region_price.svg", "Observed prices by region code", "Region code", "Price (USD)", [(["Caribbean","Europe","USA"].index(r["region"]), r["price"]) for r in rows if r["region"] in ["Caribbean","Europe","USA"]])
    svg(FIG / "process_q1_log_length.svg", "Model feature: log price vs length", "Length (ft)", "log(price)", [(r["length"], math.log(r["price"])) for r in rows])
    svg(FIG / "process_q1_residuals.svg", "Cross-validated residuals", "Observed price (USD)", "Observed - predicted (USD)", [(a, a-p) for a,p in zip(all_actual, all_pred)])
    svg(FIG / "process_q1_fold_rmse.svg", "Cross-validation fold RMSE", "Fold", "RMSE (USD)", [(x["fold"], x["rmse_usd"]) for x in cv_records])
    svg(FIG / "result_q1_pred_observed.svg", "Cross-validated predictions", "Observed price (USD)", "Predicted price (USD)", list(zip(all_actual, all_pred)))
    svg(FIG / "result_q1_hull_fit.svg", "In-sample fit by hull type", "Length (ft)", "Predicted price (USD)", [(r["length"], fitted[i]) for i,r in enumerate(rows)])
    svg(FIG / "result_q1_region_medians.svg", "Regional median listing prices", "Region code", "Median price (USD)", [(["Caribbean","Europe","USA"].index(reg), regional[h][reg]["median_usd"]) for h in regional for reg in regional[h] if regional[h][reg]["median_usd"] is not None])
    report = {
        "problem_framing": "Explain used sailboat listing prices and region effects; Hong Kong comparison requires external listings not present in the supplied summary.",
        "data_audit": {"source": str(SUMMARY_PATH), "source_sha256": summary["data_sha256"], "rows_used": len(rows), "by_hull": {h: len(v) for h,v in split.items()}, "fields": ["Make","Variant","Length","Geographic Region","Country/Region/State","Listing Price","Year"], "missing_rows_inferred": False},
        "assumptions": ["2020 minus manufacture year is age", "log-price residuals are approximately additive", "Europe is the reference region", "no supplemental data used"],
        "candidate_models": ["median-by-hull baseline", "log-linear regression with length, age, hull and region indicators"],
        "baseline": baseline_metrics,
        "math_specification": "log(P_i)=beta0+beta1*Length_i+beta2*Age_i+beta3*Catamaran_i+gamma_C*I(Caribbean)+gamma_U*I(USA)+epsilon_i",
        "experiment": {"cv": "deterministic 5-fold by sorted row index modulo 5", "model_cv": model_metrics, "folds": cv_records},
        "validation": {"in_sample_by_hull": by_hull},
        "sensitivity_robustness": "Compare CV metrics with hull-median baseline; region medians reported by hull.",
        "falsification": "A useful model should beat the baseline on CV RMSE/MAE; this check is recorded numerically.",
        "regional_descriptives": regional,
        "reviewer_risks": ["Listing prices are asking prices, not transaction prices", "Rows_data is the only permitted data source", "Model omits unobserved equipment and condition", "Hong Kong effect is pending external comparable data"],
        "pending_stages": ["Hong Kong comparable-listing modeling and external-data source audit", "official contest-format verification"],
        "reproducibility": {"python": sys.version, "platform": platform.platform(), "command": "python prototype_model.py", "seed": 0, "input_sha256": summary["data_sha256"]},
    }
    (OUT / "metrics.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    with (OUT / "predictions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["hull","length","year","region","actual_price","cv_predicted_price"])
        for r, p in zip(rows, fitted): w.writerow([r["hull"], r["length"], r["year"], r["region"], r["price"], round(p, 2)])
    (OUT / "repro_manifest.json").write_text(json.dumps(report["reproducibility"], indent=2), encoding="utf-8")
    print(json.dumps({"rows_used": len(rows), "model_cv": model_metrics, "baseline_cv": baseline_metrics, "figures": len(list(FIG.glob("*.svg")))}, indent=2))


if __name__ == "__main__":
    main()

import json, hashlib, platform, sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
SUMMARY = Path(r"C:/Users/伍辰杰/Documents/ChatGPT/mathmodel/math-modeling-competition-skills/benchmarks/case-summaries/mcm-2023-y.json")
OUT = ROOT / "results"
FIG = ROOT / "figures"
OUT.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

def load_data():
    obj = json.loads(SUMMARY.read_text(encoding="utf-8"))
    frames = []
    audit = obj["data_audit"][0] if isinstance(obj["data_audit"], list) else obj["data_audit"]
    for sheet in audit["sheets"]:
        rows = sheet["rows_data"]
        cols = [str(x).strip().replace("\n", " ") for x in rows[0]]
        df = pd.DataFrame(rows[1:], columns=cols)
        df["hull_type"] = "catamaran" if "Catamaran" in sheet["sheet"] else "monohull"
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    for c in ["Make", "Variant", "Geographic Region", "Country/Region/State"]:
        df[c] = df[c].fillna("").astype(str).str.replace("\u00a0", " ", regex=False).str.strip()
    df["length_ft"] = pd.to_numeric(df["Length (ft)"], errors="coerce")
    df["price_usd"] = pd.to_numeric(df["Listing Price (USD)"], errors="coerce")
    df["year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df.dropna(subset=["length_ft", "price_usd", "year"])
    df = df[(df.price_usd > 0) & (df.length_ft > 0)]
    df["age"] = 2020 - df["year"]
    df["log_price"] = np.log(df["price_usd"].to_numpy(float))
    return obj, df

def design(df, variant=False):
    regions = ["Caribbean", "Europe", "USA"]
    X = [np.ones(len(df)), df["length_ft"].to_numpy(float), df["age"].to_numpy(float), (df.hull_type == "catamaran").to_numpy(float)]
    names = ["intercept", "length_ft", "age_years", "catamaran"]
    for r in regions[1:]:
        z = (df["Geographic Region"] == r).to_numpy(float)
        X.append(z); names.append("region_" + r.lower())
        X.append(z * df["length_ft"].to_numpy(float)); names.append("length_x_region_" + r.lower())
    if variant:
        # Rare variants are retained but ridge-regularized to avoid singularity.
        counts = df["Variant"].value_counts()
        for v in sorted(counts[counts >= 3].index):
            if v:
                X.append((df["Variant"] == v).to_numpy(float)); names.append("variant=" + v)
    return np.column_stack(X), names

def ridge_fit(X, y, lam=10.0):
    A = X.T @ X + lam * np.eye(X.shape[1]); A[0, 0] -= lam
    return np.linalg.solve(A, X.T @ y)

def metrics(y, pred):
    err = y - pred
    return {"rmse_log": float(np.sqrt(np.mean(err**2))), "mae_log": float(np.mean(np.abs(err))),
            "rmse_usd": float(np.sqrt(np.mean((np.exp(y)-np.exp(pred))**2))),
            "median_ape": float(np.median(np.abs(np.exp(err)-1.0)))}

def cv(df, variant=False, k=5):
    X, names = design(df, variant); y = df.log_price.to_numpy(float); n = len(df)
    fold = np.arange(n) % k; preds = np.empty(n)
    for f in range(k):
        tr, te = fold != f, fold == f
        beta = ridge_fit(X[tr], y[tr], 10.0 if variant else 1e-8)
        preds[te] = X[te] @ beta
    return metrics(y, preds), preds, names

def svg(path, title, xs, ys, xlab, ylab):
    w, h, ml, mb = 720, 440, 70, 55
    xmin, xmax = float(min(xs)), float(max(xs)); ymin, ymax = float(min(ys)), float(max(ys))
    if xmax == xmin: xmax += 1
    if ymax == ymin: ymax += 1
    def px(x): return ml + (x-xmin)/(xmax-xmin)*(w-ml-25)
    def py(y): return h-mb - (y-ymin)/(ymax-ymin)*(h-mb-25)
    pts = " ".join(f"{px(x):.1f},{py(y):.1f}" for x,y in zip(xs,ys))
    body = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{w/2}" y="25" text-anchor="middle" font-family="Arial" font-size="16">{title}</text>', f'<line x1="{ml}" y1="{h-mb}" x2="{w-25}" y2="{h-mb}" stroke="black"/><line x1="{ml}" y1="{h-mb}" x2="{ml}" y2="25" stroke="black"/>', f'<polyline fill="none" stroke="#0072B2" stroke-width="2" points="{pts}"/>']
    for x,y in zip(xs,ys): body.append(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="3" fill="#D55E00"/>')
    body += [f'<text x="{w/2}" y="{h-12}" text-anchor="middle" font-family="Arial" font-size="12">{xlab}</text>', f'<text x="15" y="{h/2}" transform="rotate(-90 15 {h/2})" text-anchor="middle" font-family="Arial" font-size="12">{ylab}</text>', '</svg>']
    path.write_text("\n".join(body), encoding="utf-8")

def main():
    obj, df = load_data()
    base = df.groupby("hull_type")["price_usd"].median().to_dict()
    baseline_pred = df.hull_type.map(base).to_numpy(float)
    baseline = metrics(df.log_price.to_numpy(float), np.log(baseline_pred))
    m1, p1, names1 = cv(df, False); m2, p2, names2 = cv(df, True)
    X, _ = design(df, False); beta = ridge_fit(X, df.log_price.to_numpy(float), 1e-8)
    resid = df.log_price.to_numpy(float) - X @ beta
    region_effect = {n: float(b) for n,b in zip(names1,beta) if n.startswith("region_")}
    report = {
      "problem_framing": {"q1":"Explain listing price and prediction precision", "q2":"Estimate region effects", "q3":"Assess Hong Kong effect for a subset", "q4":"Other inferences"},
      "data_audit": {"source": str(SUMMARY), "problem_sha256": obj.get("problem_sha256"), "data_sha256": obj.get("data_sha256"), "rows_used": int(len(df)), "by_hull": df.hull_type.value_counts().to_dict(), "missing_location_fields": int(((df["Country/Region/State"] == "") | (df["Geographic Region"] == "")).sum()), "price_range_usd": [float(df.price_usd.min()), float(df.price_usd.max())]},
      "assumptions": ["2020 listing year is the reference date; age=2020-manufacture year", "log-price errors are approximately homoscedastic", "Caribbean is the reference region", "no supplemental data are used"],
      "candidate_models": ["Hull-type median baseline", "Pooled log-price ridge regression with length, age, hull, region, and length-region interactions", "Variant fixed effects with ridge regularization"],
      "baseline": baseline,
      "math_specification": {"equation":"log(P_i)=beta0+beta1 L_i+beta2 age_i+beta3 Cat_i+gamma_r R_ir+delta_r L_i R_ir+epsilon_i", "precision":"95% log-scale interval approximated by fitted value +/- 1.96*sigma; sigma is residual SD"},
      "experiment": {"k_folds":5,"fold_assignment":"row_index mod 5","model_main":m1,"model_variant":m2,"residual_sd_log":float(np.std(resid, ddof=1))},
      "validation": {"metric":"RMSE/MAE on log price; USD RMSE and median absolute percent error also reported", "main_cv":m1, "variant_cv":m2},
      "sensitivity_robustness": {"region_coefficients_log_price":region_effect, "price_multiplier_vs_caribbean":{k:float(np.exp(v)) for k,v in region_effect.items()}, "variant_count_in_model":len(names2)-len(names1)},
      "falsification": ["Refit after excluding each hull type", "Compare region coefficients with and without length interactions", "Check residuals by year and region"],
      "reviewer_risks": ["Rows are advertised listings, not transaction prices", "Variant naming inconsistencies and duplicate listings may remain", "Omitted boat features can confound region effects", "Hong Kong comparison is unidentified without Hong Kong data"],
      "pending_stages": ["q3_hong_kong_comparable_prices"],
    }
    (OUT/"modeling_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame({"actual_price_usd":np.exp(df.log_price),"pred_main_usd":np.exp(p1),"pred_variant_usd":np.exp(p2),"hull_type":df.hull_type,"region":df["Geographic Region"]}).to_csv(OUT/"predictions.csv", index=False)
    # Nine deterministic SVG figures: three evidence classes for q1-q3; q3 is marked unavailable.
    q1 = df.groupby("year").price_usd.median().sort_index(); q2 = df.groupby("Geographic Region").price_usd.median().sort_index(); q3 = df.groupby("hull_type").price_usd.median().sort_index()
    specs = [("raw_q1_price_by_year.svg","Raw prices by manufacture year",q1.index,q1.values,"Year","Median USD"),("raw_q2_region_medians.svg","Raw regional medians",range(len(q2)),q2.values,"Region index","Median USD"),("raw_q3_hull_medians.svg","Raw medians by hull type",range(len(q3)),q3.values,"Hull index","Median USD"),("process_q1_cv_predictions.svg","Cross-validation predictions",df.price_usd.iloc[::max(1,len(df)//120)],np.exp(p1[::max(1,len(df)//120)]),"Row order","USD"),("process_q2_region_coefficients.svg","Estimated regional log effects",range(len(region_effect)),list(region_effect.values()),"Coefficient index","Log effect"),("process_q3_hull_counts.svg","Rows by hull type",range(len(q3)),df.hull_type.value_counts().reindex(q3.index).values,"Hull index","Count"),("result_q1_actual_vs_pred.svg","Actual versus predicted price",np.exp(df.log_price.iloc[::max(1,len(df)//120)]),np.exp(p1[::max(1,len(df)//120)]),"Actual USD","Predicted USD"),("result_q2_region_multipliers.svg","Regional price multipliers",range(len(region_effect)),[np.exp(v) for v in region_effect.values()],"Coefficient index","Multiplier"),("result_q3_hk_pending.svg","Hong Kong comparison unavailable",[0,1],[0,0],"Status","No supplied HK data")]
    for name,title,xs,ys,xlab,ylab in specs: svg(FIG/name,title,list(xs),list(ys),xlab,ylab)
    manifest = {"generated_utc":datetime.now(timezone.utc).isoformat(),"python":sys.version,"platform":platform.platform(),"seed":0,"input_path":str(SUMMARY),"input_sha256":hashlib.sha256(SUMMARY.read_bytes()).hexdigest(),"command":"python run_model.py","dependencies":{"numpy":np.__version__,"pandas":pd.__version__}}
    (OUT/"reproducibility_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT/"metrics.json").write_text(json.dumps({"rows_used":len(df),"baseline":baseline,"main_cv":m1,"variant_cv":m2,"figures_count":len(specs),"pending_stages":report["pending_stages"]}, indent=2), encoding="utf-8")
    print(json.dumps({"rows_used":len(df),"main_cv":m1,"variant_cv":m2,"figures_count":len(specs)}, separators=(",",":")))

if __name__ == "__main__": main()

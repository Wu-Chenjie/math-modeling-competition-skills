#!/usr/bin/env python3
"""Deterministic analysis of the audited MCM 2023 Wordle rows."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np


def load_audited_rows(case_path: Path):
    data = json.loads(Path(case_path).read_text(encoding="utf-8"))
    sheet = data["data_audit"][0]["sheets"][0]
    raw_rows = sheet["rows_data"]
    rows = []
    for raw in raw_rows[2:]:
        if len(raw) < 13 or not raw[1] or not raw[2] or not raw[3]:
            continue
        try:
            serial = int(float(raw[1]))
            dt = date(1899, 12, 30) + timedelta(days=serial)
            vals = [float(x) for x in raw[4:13]]
        except (TypeError, ValueError, OverflowError):
            continue
        if len(vals) != 9 or vals[0] <= 0:
            continue
        rows.append({
            "date": dt,
            "contest": int(float(raw[2])),
            "word": str(raw[3]).strip().lower(),
            "reported": vals[0],
            "hard_mode": vals[1],
            "distribution": vals[2:],
        })
    rows.sort(key=lambda r: r["date"])
    audit = {
        "audited_sheet_rows": int(sheet["rows"]),
        "audited_columns": int(sheet["columns"]),
        "nonempty_cells": int(sheet["nonempty_cells"]),
        "valid_data_rows": len(rows),
        "date_min": rows[0]["date"].isoformat() if rows else None,
        "date_max": rows[-1]["date"].isoformat() if rows else None,
        "omitted_rows_not_invented": True,
    }
    return rows, audit


def build_word_features(words):
    names = ["vowel_count", "unique_letters", "repeat_excess", "letter_sum", "contains_e"]
    features = []
    for word in words:
        letters = [c for c in str(word).lower() if c.isalpha()]
        counts = {c: letters.count(c) for c in set(letters)}
        features.append([
            float(sum(c in "aeiou" for c in letters)),
            float(len(set(letters))),
            float(sum(max(0, n - 1) for n in counts.values())),
            float(sum(ord(c) - 96 for c in letters)),
            float("e" in letters),
        ])
    return names, np.asarray(features, dtype=float)


def alr_transform(percentages):
    p = np.asarray(percentages, dtype=float) / 100.0
    p = np.clip(p, 1e-8, None)
    p = p / p.sum(axis=-1, keepdims=True)
    return np.log(p[..., :-1] / p[..., -1:])


def alr_inverse(values):
    z = np.asarray(values, dtype=float)
    ex = np.exp(np.clip(np.concatenate([z, np.zeros((*z.shape[:-1], 1))], axis=-1), -50, 50))
    return 100.0 * ex / ex.sum(axis=-1, keepdims=True)


def rolling_origin_splits(n, horizon=30, min_train=180):
    splits = []
    start = min_train
    while start + horizon <= n:
        splits.append((np.arange(start), np.arange(start, start + horizon)))
        start += horizon
    return splits


def _ols_fit(x, y):
    x1 = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(x1, y, rcond=None)
    return beta


def _ols_predict(beta, x):
    return np.column_stack([np.ones(len(x)), x]) @ beta


def _svg(path: Path, title: str, x, y, y2=None, xlabel="index", ylabel="value"):
    width, height, margin = 760, 430, 60
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    series = [y] + ([] if y2 is None else [np.asarray(y2, dtype=float)])
    ymin = min(float(np.min(s)) for s in series); ymax = max(float(np.max(s)) for s in series)
    if ymax == ymin: ymax = ymin + 1
    def pts(s):
        return " ".join(f"{margin + (width-2*margin)*i/max(1,len(s)-1):.1f},{height-margin-(height-2*margin)*(v-ymin)/(ymax-ymin):.1f}" for i,v in enumerate(s))
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>', f'<text x="{margin}" y="28" font-family="Arial" font-size="18">{title}</text>',
             f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="#333"/>', f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="#333"/>',
             f'<polyline fill="none" stroke="#1769aa" stroke-width="2" points="{pts(y)}"/>']
    if y2 is not None: lines.append(f'<polyline fill="none" stroke="#d55e00" stroke-width="2" points="{pts(series[1])}"/>')
    lines += [f'<text x="{width/2-30}" y="{height-10}" font-family="Arial" font-size="12">{xlabel}</text>', f'<text x="14" y="{height/2}" font-family="Arial" font-size="12" transform="rotate(-90 14 {height/2})">{ylabel}</text>', '</svg>']
    path.write_text("\n".join(lines), encoding="utf-8")


def analyze(rows, output: Path, case_path: Path):
    output.mkdir(parents=True, exist_ok=True); figures = output / "figures"; figures.mkdir(exist_ok=True); results = output / "results"; results.mkdir(exist_ok=True)
    n = len(rows); reported = np.array([r["reported"] for r in rows]); hard = np.array([r["hard_mode"] / r["reported"] for r in rows]); dist = np.array([r["distribution"] for r in rows]);
    words = [r["word"] for r in rows] + ["eerie"]; feature_names, feat_all = build_word_features(words); feat = feat_all[:-1]; eerie_feat = feat_all[-1:]
    # Time-series model: log-linear trend + weekday Fourier terms, with residual bootstrap PI.
    t = np.arange(n, dtype=float); dow = np.array([r["date"].weekday() for r in rows]); x_time = np.column_stack([t, np.sin(2*np.pi*t/7), np.cos(2*np.pi*t/7)])
    beta_time = _ols_fit(x_time, np.log1p(reported)); fitted_log = _ols_predict(beta_time, x_time); residuals = np.log1p(reported) - fitted_log
    # Last audited date is 2022-12-31; March 1, 2023 is 60 calendar days later.
    horizon_days = (date(2023, 3, 1) - rows[-1]["date"]).days
    future_t = np.array([n - 1 + horizon_days], dtype=float); future_x = np.column_stack([future_t, np.sin(2*np.pi*future_t/7), np.cos(2*np.pi*future_t/7)]); point = float(np.expm1(_ols_predict(beta_time, future_x)[0]));
    rng = np.random.default_rng(20230301); boot = np.array([np.expm1(_ols_predict(beta_time, future_x)[0] + rng.choice(residuals)) for _ in range(4000)]); pi = [float(np.quantile(boot, .025)), float(np.quantile(boot, .975))]
    # Compositional outcome model on ALR coordinates using word features and smooth time trend.
    z = alr_transform(dist); x_comp = np.column_stack([feat, t / max(1, n-1)]); comp_betas = np.column_stack([_ols_fit(x_comp, z[:, j]) for j in range(z.shape[1])]); eerie_z = _ols_predict(comp_betas, np.column_stack([eerie_feat, [[1.0]]]))[0]; eerie_pred = alr_inverse(eerie_z)
    # Hard-mode share and difficulty classification (difficulty = expected solve score).
    x_word = np.column_stack([feat, t / max(1, n-1)]); hard_beta = _ols_fit(x_word, hard); hard_pred = np.clip(_ols_predict(hard_beta, x_word), 0, 1); solve_scores = np.arange(1, 8); difficulty = dist @ solve_scores / 100.0; median_diff = float(np.median(difficulty)); labels = np.where(difficulty <= np.quantile(difficulty, 1/3), "easy", np.where(difficulty <= np.quantile(difficulty, 2/3), "medium", "hard")); eerie_score = float(eerie_pred @ solve_scores / 100.0); eerie_label = "easy" if eerie_score <= np.quantile(difficulty,1/3) else ("medium" if eerie_score <= np.quantile(difficulty,2/3) else "hard")
    splits = rolling_origin_splits(n); cv_mae=[]; cv_acc=[]
    for train_idx,test_idx in splits:
        b = _ols_fit(x_time[train_idx], np.log1p(reported[train_idx])); pred = np.expm1(_ols_predict(b, x_time[test_idx])); cv_mae.append(float(np.mean(np.abs(pred-reported[test_idx]))));
        wb = _ols_fit(x_word[train_idx], hard[train_idx]); hp = np.clip(_ols_predict(wb, x_word[test_idx]),0,1); cv_acc.append(float(np.mean((hp>=np.median(hard[train_idx]))==(hard[test_idx]>=np.median(hard[train_idx])))))
    # 9 figures: three categories for each of q1-q3.
    _svg(figures/"raw_q1_reported.svg", "Raw reported results", t, reported, xlabel="day", ylabel="reported count")
    _svg(figures/"process_q1_logtrend.svg", "Processed log trend", t, np.log1p(reported), fitted_log, xlabel="day", ylabel="log(1+count)")
    _svg(figures/"result_q1_forecast.svg", "March 1 2023 forecast interval", [0,1,2], [pi[0],point,pi[1]], xlabel="lower / point / upper", ylabel="reported count")
    _svg(figures/"raw_q2_distribution.svg", "Raw solve distribution", np.arange(7), dist.mean(axis=0), xlabel="outcome", ylabel="percent")
    _svg(figures/"process_q2_alr.svg", "ALR coordinate process", t, z[:,0], z[:,1], xlabel="day", ylabel="ALR")
    _svg(figures/"result_q2_eerie.svg", "EERIE predicted distribution", np.arange(7), eerie_pred, xlabel="outcome", ylabel="percent")
    _svg(figures/"raw_q3_features.svg", "Word feature sample", np.arange(5), feat[:5,0], xlabel="sample", ylabel="vowel count")
    _svg(figures/"process_q3_difficulty.svg", "Difficulty score process", t, difficulty, xlabel="day", ylabel="expected tries")
    _svg(figures/"result_q3_classes.svg", "Difficulty classes", np.arange(3), [sum(labels==c) for c in ["easy","medium","hard"]], xlabel="class", ylabel="count")
    with (results/"summary.csv").open("w", newline="", encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["metric","value"]); w.writerows([["n_rows",n],["forecast_point",point],["forecast_pi_low",pi[0]],["forecast_pi_high",pi[1]],["hard_mode_mean",float(hard.mean())],["difficulty_median",median_diff],["eerie_expected_tries",eerie_score],["eerie_class",eerie_label],["cv_forecast_mae_mean",float(np.mean(cv_mae))],["cv_hard_accuracy_mean",float(np.mean(cv_acc))]])
    manifest={"case_id":"mcm-2023-c","input_sha256":hashlib.sha256(case_path.read_bytes()).hexdigest(),"python":platform.python_version(),"numpy":np.__version__,"seed":20230301,"command":f"python {Path(__file__).name} --input {case_path} --output {output}","rows_used":n}
    (results/"reproducibility_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    report={"problem_framing":{"title":"Predicting Wordle Results","questions":["reported-count prediction interval","hard-mode association","future outcome distribution","difficulty classification","other features"]},"data_audit":{"source":"case summary JSON rows_data only",**{k:v for k,v in load_audited_rows(case_path)[1].items()},"binary_attachments_opened":False},"assumptions":["Rows are chronological and percentages are rounded compositions.","Twitter reporters represent the modeled population but not all players.","No external lexical or social data are used."],"candidate_models":{"q1":"log-linear trend with weekly Fourier terms; residual bootstrap interval","q2":"OLS hard-mode share on intrinsic word features and time","q3":"ALR compositional regression for seven outcomes","q4":"tertile classification by expected tries with feature diagnostics"},"baseline":{"forecast":"historical mean reported count","distribution":"overall mean composition","difficulty":"tertile labels from observed expected tries"},"math_specification":{"forecast":"log(1+N_t)=beta0+beta1 t+beta2 sin(2pi t/7)+beta3 cos(2pi t/7)+epsilon_t","composition":"ALR(p_t,j)=gamma_j^T x_t; p=softmax([ALR,0])","features":feature_names},"code_prototype":{"path":str(Path(__file__).resolve()),"entrypoint":"main"},"experiment":{"rows":n,"march_1_2023":{"horizon_days":horizon_days,"point":point,"prediction_interval_95":pi},"eerie":{"distribution_percent":eerie_pred.tolist(),"expected_tries":eerie_score,"difficulty_class":eerie_label}},"validation":{"rolling_origin_splits":len(splits),"forecast_mae_mean":float(np.mean(cv_mae)),"hard_mode_accuracy_mean":float(np.mean(cv_acc)),"classification_note":"No held-out classifier package; class thresholds are descriptive."},"sensitivity_robustness":{"bootstrap_draws":4000,"seed":20230301,"composition_clipped_probability":1e-8,"temporal_leakage_control":"rolling origin"},"falsification":["Residual autocorrelation or calendar shocks would invalidate the simple forecast.","Word-feature coefficients are associative, not causal.","Rounded percentages and reporter selection limit calibration."],"reviewer_risks":["Only audited sample rows are available; omitted binary rows were not reconstructed.","March 1 is extrapolated 60 calendar days beyond the final 2022 row.","Difficulty labels depend on tertile thresholds and expected-tries proxy."],"reproducibility_manifest":manifest}
    (output/"modeling_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")


def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--input",required=True); parser.add_argument("--output",required=True); args=parser.parse_args(argv); rows,_=load_audited_rows(Path(args.input)); analyze(rows,Path(args.output),Path(args.input)); return 0


if __name__ == "__main__":
    raise SystemExit(main())

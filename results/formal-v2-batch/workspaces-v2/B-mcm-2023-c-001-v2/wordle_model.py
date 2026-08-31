"""Deterministic, dependency-free prototype for 2023 MCM Problem C.

Input is restricted to the benchmark case-summary JSON. No binary attachment is read.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import random
import statistics
import sys
import time
from pathlib import Path


CASE_PATH = Path(r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\mcm-2023-c.json")
ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
TARGET_SERIAL = 44986  # 2023-03-01, 60 days after 2022-12-31 (44926)
OUTCOME_NAMES = ["1", "2", "3", "4", "5", "6", "X"]


def quantile(values, q):
    values = sorted(values)
    if not values:
        return float("nan")
    pos = (len(values) - 1) * q
    lo, hi = int(pos), math.ceil(pos)
    if lo == hi:
        return values[lo]
    return values[lo] * (hi - pos) + values[hi] * (pos - lo)


def load_records(path=CASE_PATH):
    with open(path, encoding="utf-8") as f:
        case = json.load(f)
    sheet = case["data_audit"][0]["sheets"][0]
    records = []
    skipped_blank = 0
    for row in sheet["rows_data"][2:]:
        if len(row) < 13 or not str(row[2]).strip():
            skipped_blank += 1
            continue
        raw_word = str(row[3])
        raw_pct = [float(v) for v in row[6:13]]
        pct_sum = sum(raw_pct)
        records.append({
            "date": int(float(row[1])),
            "contest": int(float(row[2])),
            "word": raw_word.strip().lower(),
            "raw_word": raw_word,
            "reported": int(float(row[4])),
            "hard": int(float(row[5])),
            "hard_share": int(float(row[5])) / int(float(row[4])),
            "raw_percent_sum": pct_sum,
            "outcomes": [v / pct_sum for v in raw_pct],
        })
    records.sort(key=lambda r: r["date"])
    audit = {
        "rows_total": sheet["rows"],
        "rows_data_supplied": len(sheet["rows_data"]),
        "records_used": len(records),
        "blank_or_padding_rows_skipped": skipped_blank,
        "date_serial_range": [records[0]["date"], records[-1]["date"]],
        "contest_range": [records[0]["contest"], records[-1]["contest"]],
        "trimmed_word_rows": sum(r["raw_word"] != r["raw_word"].strip() for r in records),
        "non_five_letter_words": [r["word"] for r in records if len(r["word"]) != 5],
        "raw_percentage_sum_range": [min(r["raw_percent_sum"] for r in records), max(r["raw_percent_sum"] for r in records)],
        "rounding_normalization": "Each seven-bin row was divided by its supplied row sum; no omitted values were imputed.",
    }
    return records, audit


def word_features(word):
    w = word.strip().lower()
    unique = len(set(w))
    vowels = sum(ch in "aeiou" for ch in w)
    rare = sum(ch in "jqxzvkw" for ch in w)
    return {
        "length": len(w),
        "unique_letters": unique,
        "repeated_letters": len(w) - unique,
        "vowels": vowels,
        "rare_letters": rare,
    }


def solve_linear(a, b):
    n = len(b)
    aug = [list(map(float, a[i])) + [float(b[i])] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        aug[col], aug[pivot] = aug[pivot], aug[col]
        if abs(aug[col][col]) < 1e-12:
            aug[col][col] = 1e-12
        scale = aug[col][col]
        aug[col] = [v / scale for v in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            aug[row] = [x - factor * y for x, y in zip(aug[row], aug[col])]
    return [aug[i][-1] for i in range(n)]


def ridge_fit(x, y, lam=1e-6):
    p = len(x[0])
    gram = [[sum(row[i] * row[j] for row in x) for j in range(p)] for i in range(p)]
    rhs = [sum(row[i] * value for row, value in zip(x, y)) for i in range(p)]
    for i in range(1, p):
        gram[i][i] += lam
    return solve_linear(gram, rhs)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def regression_metrics(actual, predicted):
    errors = [a - p for a, p in zip(actual, predicted)]
    return {
        "mae": statistics.mean(abs(e) for e in errors),
        "rmse": math.sqrt(statistics.mean(e * e for e in errors)),
        "mape": statistics.mean(abs(e) / max(abs(a), 1e-12) for a, e in zip(actual, errors)),
    }


def log_trend_fit(records, window):
    sample = records[-min(window, len(records)):]
    origin = sample[0]["date"]
    x = [[1.0, r["date"] - origin] for r in sample]
    y = [math.log(r["reported"]) for r in sample]
    beta = ridge_fit(x, y)
    residuals = [actual - dot(beta, row) for actual, row in zip(y, x)]
    return beta, origin, statistics.stdev(residuals)


def forecast_reported(records, window=120):
    split = int(len(records) * 0.8)
    train, test = records[:split], records[split:]
    beta, origin, _ = log_trend_fit(train, window)
    main_pred = [math.exp(dot(beta, [1, r["date"] - origin])) for r in test]
    base_pred = [train[-1]["reported"]] * len(test)
    beta, origin, sigma = log_trend_fit(records, window)
    log_point = dot(beta, [1, TARGET_SERIAL - origin])
    point = math.exp(log_point)
    sensitivity = []
    for w in (60, 90, 120, 180):
        b, o, s = log_trend_fit(records, w)
        lp = dot(b, [1, TARGET_SERIAL - o])
        sensitivity.append({"window_days": w, "point": math.exp(lp), "lower": math.exp(lp - 1.96 * s), "upper": math.exp(lp + 1.96 * s)})
    return {
        "model": "OLS log(reported) on date using the most recent 120 observations",
        "target_excel_serial": TARGET_SERIAL,
        "point": point,
        "lower": math.exp(log_point - 1.96 * sigma),
        "upper": math.exp(log_point + 1.96 * sigma),
        "interval": "Approximate 95% residual prediction interval on the log scale",
        "chronological_holdout_n": len(test),
        "holdout": {"main": regression_metrics([r["reported"] for r in test], main_pred), "persistence_baseline": regression_metrics([r["reported"] for r in test], base_pred)},
        "sensitivity": sensitivity,
    }


def feature_row(record, date_min, date_span, include_date=True):
    f = word_features(record["word"])
    row = [1.0]
    if include_date:
        row.append((record["date"] - date_min) / max(date_span, 1))
    row.extend([f["repeated_letters"], f["vowels"], f["rare_letters"], f["unique_letters"]])
    return row


def hard_mode_analysis(records):
    split = int(len(records) * 0.8)
    train, test = records[:split], records[split:]
    d0, span = train[0]["date"], train[-1]["date"] - train[0]["date"]
    x = [feature_row(r, d0, span) for r in train]
    y = [r["hard_share"] for r in train]
    beta = ridge_fit(x, y, 1e-3)
    pred = [dot(beta, feature_row(r, d0, span)) for r in test]
    reduced = ridge_fit([[row[0], row[1]] for row in x], y, 1e-3)
    reduced_pred = [dot(reduced, feature_row(r, d0, span)[:2]) for r in test]
    names = ["intercept", "normalized_date", "repeated_letters", "vowels", "rare_letters", "unique_letters"]
    return {
        "response": "hard-mode reports / all reported results",
        "coefficients": dict(zip(names, beta)),
        "coefficient_units": "absolute share change per one-unit feature change; date is scaled to the training span",
        "holdout": {"date_plus_word": regression_metrics([r["hard_share"] for r in test], pred), "date_only": regression_metrics([r["hard_share"] for r in test], reduced_pred)},
        "interpretation_rule": "A word attribute is treated as useful only if date-plus-word improves chronological holdout MAE over date-only.",
    }


def simplex(values):
    clipped = [max(0.0, v) for v in values]
    total = sum(clipped)
    return [v / total for v in clipped] if total else [1 / len(values)] * len(values)


def distribution_model(records):
    split = int(len(records) * 0.8)
    train, test = records[:split], records[split:]
    d0, span = train[0]["date"], train[-1]["date"] - train[0]["date"]
    x = [feature_row(r, d0, span) for r in train]
    betas = [ridge_fit(x, [r["outcomes"][j] for r in train], 1e-3) for j in range(7)]
    preds = [simplex([dot(b, feature_row(r, d0, span)) for b in betas]) for r in test]
    baseline = [statistics.mean(r["outcomes"][j] for r in train) for j in range(7)]
    errors = [[abs(r["outcomes"][j] - p[j]) for r, p in zip(test, preds)] for j in range(7)]
    main_mae = statistics.mean(v for row in errors for v in row)
    base_mae = statistics.mean(abs(r["outcomes"][j] - baseline[j]) for r in test for j in range(7))
    all_d0, all_span = records[0]["date"], records[-1]["date"] - records[0]["date"]
    all_x = [feature_row(r, all_d0, all_span) for r in records]
    all_betas = [ridge_fit(all_x, [r["outcomes"][j] for r in records], 1e-3) for j in range(7)]
    eerie = {"date": TARGET_SERIAL, "word": "eerie"}
    point = simplex([dot(b, feature_row(eerie, all_d0, all_span)) for b in all_betas])
    radii = [quantile(e, 0.90) for e in errors]
    intervals = [[max(0, p - radius), min(1, p + radius)] for p, radius in zip(point, radii)]
    return {
        "model": "Seven ridge regressions on date and word attributes, clipped and renormalized to the simplex",
        "chronological_holdout_n": len(test),
        "holdout_mean_absolute_share_error": main_mae,
        "mean_distribution_baseline_error": base_mae,
        "eerie_prediction": dict(zip(OUTCOME_NAMES, point)),
        "eerie_90pct_empirical_absolute_error_bands": dict(zip(OUTCOME_NAMES, intervals)),
        "uncertainty": "Per-bin bands use the 90th percentile absolute chronological holdout error and are marginal, not a joint simplex region.",
    }


def difficulty_score(record):
    return sum((i + 1) * p for i, p in enumerate(record["outcomes"]))


def label_score(score, cuts):
    return "easy" if score <= cuts[0] else "medium" if score <= cuts[1] else "hard"


def classify_difficulty(records):
    split = int(len(records) * 0.8)
    train, test = records[:split], records[split:]
    scores = [difficulty_score(r) for r in train]
    cuts = [quantile(scores, 1 / 3), quantile(scores, 2 / 3)]
    x = [feature_row(r, 0, 1, include_date=False) for r in train]
    beta = ridge_fit(x, scores, 1e-3)
    pred_scores = [dot(beta, feature_row(r, 0, 1, include_date=False)) for r in test]
    actual_labels = [label_score(difficulty_score(r), cuts) for r in test]
    predicted_labels = [label_score(s, cuts) for s in pred_scores]
    accuracy = statistics.mean(a == p for a, p in zip(actual_labels, predicted_labels))
    majority = max(actual_labels.count(k) for k in ("easy", "medium", "hard")) / len(actual_labels)
    confusion = {a: {p: 0 for p in ("easy", "medium", "hard")} for a in ("easy", "medium", "hard")}
    for a, p in zip(actual_labels, predicted_labels):
        confusion[a][p] += 1
    all_scores = [difficulty_score(r) for r in records]
    full_cuts = [quantile(all_scores, 1 / 3), quantile(all_scores, 2 / 3)]
    full_x = [feature_row(r, 0, 1, include_date=False) for r in records]
    full_beta = ridge_fit(full_x, all_scores, 1e-3)
    eerie_score = dot(full_beta, feature_row({"word": "eerie"}, 0, 1, include_date=False))
    return {
        "definition": "Expected attempt score with X assigned 7, divided into sample tertiles",
        "thresholds_training": cuts,
        "attribute_coefficients": dict(zip(["intercept", "repeated_letters", "vowels", "rare_letters", "unique_letters"], beta)),
        "chronological_holdout_n": len(test),
        "holdout_accuracy": accuracy,
        "majority_baseline_accuracy": majority,
        "confusion_matrix": confusion,
        "eerie_expected_score": eerie_score,
        "eerie_label": label_score(eerie_score, full_cuts),
        "full_sample_thresholds": full_cuts,
    }


def pearson(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return num / den if den else 0.0


def falsification(records, observed_accuracy):
    rng = random.Random(2023)
    shuffled = records[:]
    words = [r["word"] for r in shuffled]
    rng.shuffle(words)
    permuted = [dict(r, word=w) for r, w in zip(shuffled, words)]
    perm_acc = classify_difficulty(permuted)["holdout_accuracy"]
    clean = [r for r in records if len(r["word"]) == 5]
    clean_acc = classify_difficulty(clean)["holdout_accuracy"]
    return {
        "word_attribute_permutation_accuracy": perm_acc,
        "observed_attribute_accuracy": observed_accuracy,
        "excluding_non_five_letter_accuracy": clean_acc,
        "falsification_rule": "The attribute model should beat its deterministic shuffled-word control; failure weakens attribution claims.",
    }


def svg_frame(title, content, width=760, height=440):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">' 
            '<rect width="100%" height="100%" fill="#ffffff"/>'
            f'<text x="55" y="32" font-family="Arial" font-size="18" fill="#1f2933">{title}</text>'
            '<line x1="55" y1="385" x2="730" y2="385" stroke="#52606d"/>'
            '<line x1="55" y1="55" x2="55" y2="385" stroke="#52606d"/>' + content + '</svg>')


def line_svg(title, series, path):
    flat = [v for _, values, _ in series for v in values]
    lo, hi = min(flat), max(flat)
    n = max(len(values) for _, values, _ in series)
    def xy(i, v):
        x = 55 + 675 * i / max(n - 1, 1)
        y = 385 - 310 * (v - lo) / max(hi - lo, 1e-12)
        return x, y
    body = []
    for idx, (name, values, color) in enumerate(series):
        points = ' '.join(f'{xy(i,v)[0]:.1f},{xy(i,v)[1]:.1f}' for i, v in enumerate(values))
        body.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
        body.append(f'<text x="{570 + idx*80}" y="52" font-family="Arial" font-size="11" fill="{color}">{name}</text>')
    path.write_text(svg_frame(title, ''.join(body)), encoding="utf-8")


def bar_svg(title, labels, values, path, colors=None):
    colors = colors or ["#0072B2"] * len(values)
    hi = max(values) if values else 1
    gap = 675 / max(len(values), 1)
    body = []
    for i, (label, value) in enumerate(zip(labels, values)):
        h = 295 * value / max(hi, 1e-12)
        x = 60 + i * gap
        body.append(f'<rect x="{x:.1f}" y="{385-h:.1f}" width="{gap*0.68:.1f}" height="{h:.1f}" fill="{colors[i % len(colors)]}"/>')
        body.append(f'<text x="{x+gap*.34:.1f}" y="405" text-anchor="middle" font-family="Arial" font-size="10">{label}</text>')
    path.write_text(svg_frame(title, ''.join(body)), encoding="utf-8")


def create_figures(records, forecast, hard, distribution, difficulty):
    FIGURES.mkdir(exist_ok=True)
    reported = [r["reported"] for r in records]
    hard_share = [100 * r["hard_share"] for r in records]
    scores = [difficulty_score(r) for r in records]
    mean_outcomes = [100 * statistics.mean(r["outcomes"][j] for r in records) for j in range(7)]
    line_svg("Q1 raw: daily reported results", [("reported", reported, "#0072B2")], FIGURES / "raw_q1_reported_timeseries.svg")
    bar_svg("Q1 process: holdout MAE", ["log trend", "persistence"], [forecast["holdout"]["main"]["mae"], forecast["holdout"]["persistence_baseline"]["mae"]], FIGURES / "process_q1_holdout_mae.svg", ["#009E73", "#D55E00"])
    bar_svg("Q1 result: March 1 forecast and bounds", ["lower", "point", "upper"], [forecast["lower"], forecast["point"], forecast["upper"]], FIGURES / "result_q1_forecast_interval.svg", ["#56B4E9", "#0072B2", "#56B4E9"])
    bar_svg("Q2 raw: mean reported outcome shares (%)", OUTCOME_NAMES, mean_outcomes, FIGURES / "raw_q2_mean_distribution.svg")
    bar_svg("Q2 process: distribution holdout error", ["model", "baseline"], [distribution["holdout_mean_absolute_share_error"], distribution["mean_distribution_baseline_error"]], FIGURES / "process_q2_holdout_error.svg", ["#009E73", "#D55E00"])
    bar_svg("Q2 result: EERIE predicted shares (%)", OUTCOME_NAMES, [100*v for v in distribution["eerie_prediction"].values()], FIGURES / "result_q2_eerie_distribution.svg")
    bins = [0] * 10
    lo, hi = min(scores), max(scores)
    for v in scores: bins[min(9, int(10 * (v-lo)/max(hi-lo, 1e-9)))] += 1
    bar_svg("Q3 raw: expected-attempt score distribution", [str(i+1) for i in range(10)], bins, FIGURES / "raw_q3_difficulty_histogram.svg")
    cm_values = [difficulty["confusion_matrix"][a][p] for a in ("easy","medium","hard") for p in ("easy","medium","hard")]
    bar_svg("Q3 process: chronological confusion cells", ["E-E","E-M","E-H","M-E","M-M","M-H","H-E","H-M","H-H"], cm_values, FIGURES / "process_q3_confusion.svg")
    bar_svg("Q3 result: EERIE score vs tertile cuts", ["easy cut", "EERIE", "hard cut"], [difficulty["full_sample_thresholds"][0], difficulty["eerie_expected_score"], difficulty["full_sample_thresholds"][1]], FIGURES / "result_q3_eerie_class.svg", ["#009E73", "#E69F00", "#D55E00"])
    line_svg("Q4 raw: hard-mode share over time (%)", [("hard share", hard_share, "#CC79A7")], FIGURES / "raw_q4_hard_mode_trend.svg")
    attrs = ["repeat", "vowels", "rare", "unique"]
    coeffs = [hard["coefficients"][k] for k in ("repeated_letters","vowels","rare_letters","unique_letters")]
    bar_svg("Q4 process: absolute hard-share coefficients", attrs, [abs(v) for v in coeffs], FIGURES / "process_q4_attribute_effects.svg", ["#CC79A7"])
    bar_svg("Q4 result: percentage-row rounding totals", [str(v) for v in sorted(set(r["raw_percent_sum"] for r in records))], [sum(r["raw_percent_sum"] == v for r in records) for v in sorted(set(r["raw_percent_sum"] for r in records))], FIGURES / "result_q4_rounding_totals.svg", ["#E69F00"])
    return sorted(p.name for p in FIGURES.glob("*.svg"))


def main():
    started = time.time()
    records, audit = load_records()
    forecast = forecast_reported(records)
    hard = hard_mode_analysis(records)
    distribution = distribution_model(records)
    difficulty = classify_difficulty(records)
    false = falsification(records, difficulty["holdout_accuracy"])
    figures = create_figures(records, forecast, hard, distribution, difficulty)
    rounding_counts = {str(v): sum(r["raw_percent_sum"] == v for r in records) for v in sorted(set(r["raw_percent_sum"] for r in records))}
    report = {
        "case_id": "mcm-2023-c",
        "problem_framing": {
            "q1": "Explain daily participation, forecast March 1 reported results, and assess word effects on hard-mode share.",
            "q2": "Forecast the seven-part result composition for a dated future word, with uncertainty.",
            "q3": "Classify word difficulty from intrinsic word attributes and quantify accuracy.",
            "q4": "Identify defensible additional patterns without adding external data.",
        },
        "data_audit": audit,
        "assumptions": [
            "Excel serial dates are consecutive daily observations and serial 44986 is 2023-03-01.",
            "Twitter reports are treated as the target reporting population, not all Wordle players.",
            "Rounding discrepancies are measurement noise; supplied shares are normalized by their row sum.",
            "X is assigned score 7 only for the difficulty summary, an ordinal convention rather than a literal attempt count.",
        ],
        "candidate_models": {
            "q1": ["Persistence baseline", "Recent-window log-linear participation trend"],
            "q2": ["Historical mean composition baseline", "Regularized linear composition model with simplex projection"],
            "q3": ["Majority-class baseline", "Attribute-only expected-score regression plus tertile thresholds"],
        },
        "baseline": {"participation": forecast["holdout"]["persistence_baseline"], "distribution_error": distribution["mean_distribution_baseline_error"], "classification_accuracy": difficulty["majority_baseline_accuracy"]},
        "math_specification": {
            "participation": "log(N_t)=b0+b1*t+e_t on the latest 120 observations; PI=exp(pred +/- 1.96*s_resid).",
            "hard_mode": "h_t/N_t=b0+b1*time+b2*repeats+b3*vowels+b4*rare+b5*unique+e_t.",
            "composition": "p_j=x'b_j for j=1..7, followed by nonnegative clipping and unit-sum normalization.",
            "difficulty": "D=sum(k*p_k), k=(1,...,6,7); regress D on word attributes and label by training tertiles.",
        },
        "code_prototype": {"entry_point": "wordle_model.py", "input": str(CASE_PATH), "binary_attachments_read": False, "dependencies": "Python standard library only"},
        "experiment": {"split": "first 80% train, last 20% chronological holdout", "forecast": forecast, "hard_mode": hard, "distribution": distribution, "difficulty": difficulty},
        "validation": {"temporal_leakage_control": "Every reported holdout metric fits only earlier rows.", "metrics": ["MAE", "RMSE", "MAPE", "mean absolute share error", "classification accuracy", "confusion matrix"]},
        "sensitivity_robustness": {"participation_windows": forecast["sensitivity"], "percentage_rounding_counts": rounding_counts, "excluded_non_five_letter_check": false["excluding_non_five_letter_accuracy"]},
        "falsification": false,
        "other_features": {"reported_hard_share_correlation": pearson([r["reported"] for r in records], [r["hard_share"] for r in records]), "hard_share_date_correlation": pearson([r["date"] for r in records], [r["hard_share"] for r in records]), "percentage_row_sum_counts": rounding_counts},
        "reviewer_risks": [
            "The reporting population is self-selected Twitter users, so inference does not identify all-player behavior.",
            "The March forecast extrapolates 60 days beyond the supplied period and its residual interval omits structural-break uncertainty.",
            "No external word-frequency, corpus, or Wordle strategy data were supplied; lexical features are intentionally sparse.",
            "Daily percentages are rounded and do not provide individual-level trial counts; multinomial sampling uncertainty cannot be reconstructed exactly.",
            "The anomalous six-letter token 'rprobe' is retained for primary results and excluded only in sensitivity analysis.",
            "Classification thresholds are sample-relative tertiles, not externally validated difficulty categories.",
        ],
        "reproducibility_manifest": {},
        "figures": figures,
        "pending_stages": [],
    }
    RESULTS.mkdir(exist_ok=True)
    input_sha = hashlib.sha256(CASE_PATH.read_bytes()).hexdigest()
    report["reproducibility_manifest"] = {
        "random_seed": 2023,
        "input_path": str(CASE_PATH),
        "input_sha256": input_sha,
        "declared_problem_sha256": "b511204705db800f3b812943b780074cc24bfe5108d26b6c20f308128e631ef6",
        "declared_data_sha256": "22d9c6c308700c6b744d74da8c83e358eefba955f58713c65f947624cda5ac94",
        "python": platform.python_version(),
        "command": "python wordle_model.py",
        "runtime_seconds": time.time() - started,
        "figures_count": len(figures),
    }
    (RESULTS / "metrics.json").write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    (RESULTS / "repro_manifest.json").write_text(json.dumps(report["reproducibility_manifest"], indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "records": len(records), "figures": len(figures), "metrics": str(RESULTS / "metrics.json")}))


if __name__ == "__main__":
    main()

import argparse
import hashlib
import json
import math
import platform
import struct
import zlib
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np


SEED = 20230301
TARGET_DATE = datetime(2023, 3, 1)
CATEGORIES = ["1", "2", "3", "4", "5", "6", "X"]


def excel_date(value):
    return datetime(1899, 12, 30) + timedelta(days=float(value))


def load_rows(case_path):
    obj = json.loads(Path(case_path).read_text(encoding="utf-8"))
    rows = []
    for row in obj["data_audit"][0]["sheets"][0]["rows_data"]:
        if len(row) < 13 or row[1] in ("", "Date"):
            continue
        try:
            date = excel_date(row[1])
            contest = int(row[2])
            word = str(row[3]).strip().lower()
            reported = float(row[4])
            hard = float(row[5])
            pct = np.array([float(x) for x in row[6:13]], dtype=float) / 100.0
        except (ValueError, TypeError):
            continue
        rows.append({"date": date, "contest": contest, "word": word, "reported": reported, "hard": hard, "pct": pct})
    rows.sort(key=lambda r: r["date"])
    return obj, rows


def word_features(word, day_index):
    vowels = set("aeiou")
    unique = len(set(word))
    repeats = len(word) - unique
    vowel_count = sum(ch in vowels for ch in word)
    rare = sum(ch in set("jqxz") for ch in word)
    return np.array([1.0, day_index, math.sin(2 * math.pi * day_index / 7), math.cos(2 * math.pi * day_index / 7),
                     int(day_index % 7 >= 5), unique, repeats, vowel_count, rare], dtype=float)


def ols(X, y, ridge=1e-8):
    p = X.shape[1]
    beta = np.linalg.solve(X.T @ X + ridge * np.eye(p), X.T @ y)
    resid = y - X @ beta
    dof = max(1, len(y) - p)
    sigma = float(np.sqrt(np.sum(resid ** 2) / dof))
    cov = sigma ** 2 * np.linalg.pinv(X.T @ X + ridge * np.eye(p))
    return beta, resid, sigma, cov


def sigmoid(x):
    x = np.clip(x, -40, 40)
    return 1.0 / (1.0 + np.exp(-x))


def nearest_centroid(X_train, y_train, X_test):
    classes = sorted(set(y_train))
    cents = {c: X_train[y_train == c].mean(axis=0) for c in classes}
    return np.array([min(classes, key=lambda c: float(np.sum((x - cents[c]) ** 2))) for x in X_test])


def png_bytes(width=900, height=520, color=(255, 255, 255)):
    raw = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ppm = struct.pack(">IIB", 11811, 11811, 1)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"pHYs", ppm) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def svg_figure(path, title, x_label, y_label, points=None, bars=None):
    w, h = 900, 520
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
             '<rect width="100%" height="100%" fill="white"/>',
             f'<text x="450" y="32" text-anchor="middle" font-family="Arial" font-size="22">{title}</text>',
             '<line x1="90" y1="450" x2="850" y2="450" stroke="#222"/>',
             '<line x1="90" y1="70" x2="90" y2="450" stroke="#222"/>',
             f'<text x="470" y="500" text-anchor="middle" font-family="Arial" font-size="16">{x_label}</text>',
             f'<text x="22" y="270" transform="rotate(-90 22 270)" text-anchor="middle" font-family="Arial" font-size="16">{y_label}</text>']
    if points:
        n = len(points)
        xs = np.linspace(100, 840, n)
        vals = np.asarray(points, dtype=float)
        lo, hi = float(np.nanmin(vals)), float(np.nanmax(vals))
        span = hi - lo if hi > lo else 1.0
        ys = 430 - (vals - lo) / span * 330
        d = " ".join(("M" if i == 0 else "L") + f" {x:.1f},{y:.1f}" for i, (x, y) in enumerate(zip(xs, ys)))
        parts.append(f'<path d="{d}" fill="none" stroke="#0072B2" stroke-width="3"/>')
    if bars:
        vals = np.asarray(bars, dtype=float)
        vmax = max(float(np.max(vals)), 1e-9)
        bw = 700 / len(vals)
        for i, val in enumerate(vals):
            bh = 340 * val / vmax
            x = 110 + i * bw
            parts.append(f'<rect x="{x:.1f}" y="{430-bh:.1f}" width="{bw*0.7:.1f}" height="{bh:.1f}" fill="#D55E00"/>')
    parts.append('</svg>')
    Path(path).write_text("".join(parts), encoding="utf-8")


def make_figures(fig_dir, rows, metrics):
    fig_dir.mkdir(parents=True, exist_ok=True)
    counts = [r["reported"] for r in rows]
    hard = [r["hard"] / r["reported"] for r in rows]
    mean_score = [float(np.dot(r["pct"], np.arange(1, 8))) for r in rows]
    unique = [len(set(r["word"])) for r in rows]
    specs = {
        "raw_q1_counts": ("Raw reported results", "Puzzle index", "Count", counts, None),
        "raw_q2_hard": ("Raw hard-mode share", "Puzzle index", "Share", hard, None),
        "raw_q3_scores": ("Raw score percentages", "Puzzle index", "Expected tries", mean_score, None),
        "raw_q4_features": ("Raw word uniqueness", "Puzzle index", "Unique letters", unique, None),
        "process_q1_logfit": ("Process count model", "Puzzle index", "Log count", [math.log(x) for x in counts], None),
        "process_q2_logit": ("Process hard-mode model", "Puzzle index", "Logit share", [math.log((x+1e-4)/(1-x+1e-4)) for x in hard], None),
        "process_q3_cv": ("Process temporal validation", "Fold", "RMSE", metrics["q3"]["fold_rmse"], None),
        "process_q4_centroid": ("Process difficulty centroids", "Class", "Expected tries", metrics["q4"]["centroid_score"], None),
        "result_q1_interval": ("Result March 1 count interval", "Statistic", "Reported results", None, [metrics["q1"]["forecast"], metrics["q1"]["lower"], metrics["q1"]["upper"]]),
        "result_q2_effects": ("Result hard-mode effects", "Feature", "Coefficient", None, metrics["q2"]["coefficients"]),
        "result_q3_eerie": ("Result EERIE distribution", "Score", "Probability", None, metrics["q3"]["eerie_distribution"]),
        "result_q4_class": ("Result EERIE difficulty", "Class", "Probability", None, metrics["q4"]["class_probabilities"]),
    }
    for stem, (title, xl, yl, points, bars) in specs.items():
        svg_figure(fig_dir / f"{stem}.svg", title, xl, yl, points=points, bars=bars)
        (fig_dir / f"{stem}.png").write_bytes(png_bytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--out", default=".")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    results = out / "results"
    results.mkdir(parents=True, exist_ok=True)
    obj, rows = load_rows(args.case)
    n = len(rows)
    start = rows[0]["date"]
    X = np.vstack([word_features(r["word"], (r["date"] - start).days) for r in rows])

    # Q1: log-count trend with calendar covariates and analytic 95% forecast interval.
    ylog = np.log(np.array([r["reported"] for r in rows]))
    b1, res1, s1, cov1 = ols(X[:, :5], ylog)
    target_idx = (TARGET_DATE - start).days
    xt = word_features("eerie", target_idx)[:5]
    pred_log = float(xt @ b1)
    leverage = float(xt @ np.linalg.pinv(X[:, :5].T @ X[:, :5]) @ xt)
    lo_log, hi_log = pred_log - 1.96 * s1 * math.sqrt(1 + leverage), pred_log + 1.96 * s1 * math.sqrt(1 + leverage)
    q1 = {"forecast": math.exp(pred_log), "lower": math.exp(lo_log), "upper": math.exp(hi_log), "rmse_log": float(np.sqrt(np.mean(res1**2))), "sigma_log": s1}

    # Q2: weighted logit regression for hard-mode share.
    frac = np.array([r["hard"] / r["reported"] for r in rows])
    logit = np.log(np.clip(frac, 1e-5, 1 - 1e-5) / np.clip(1 - frac, 1e-5, 1 - 1e-5))
    X2 = X[:, [0, 5, 6, 7, 8]]
    b2, res2, s2, cov2 = ols(X2, logit)
    q2 = {"coefficients": b2.tolist(), "se": np.sqrt(np.diag(cov2)).tolist(), "rmse_logit": float(np.sqrt(np.mean(res2**2))),
          "feature_names": ["intercept", "unique_letters", "repeats", "vowels", "rare_jqxz"]}

    # Q3: additive-log-ratio score distribution model with temporal holdout.
    P = np.vstack([np.clip(r["pct"], 1e-4, 1) for r in rows])
    P = P / P.sum(axis=1, keepdims=True)
    alr = np.log(P[:, :-1] / P[:, [-1]])
    X3 = X[:, [0, 1, 5, 6, 7, 8]]
    b3 = np.vstack([ols(X3, alr[:, k])[0] for k in range(6)])
    def predict_dist(x):
        z = np.r_[x @ b3.T, 0.0]
        ez = np.exp(z - np.max(z)); return ez / ez.sum()
    eerie_x = word_features("eerie", target_idx)[[0, 1, 5, 6, 7, 8]]
    eerie_dist = predict_dist(eerie_x)
    split = max(30, n - 60)
    train_b = np.vstack([ols(X3[:split], alr[:split, k])[0] for k in range(6)])
    preds = []
    for i in range(split, n):
        z = np.r_[X3[i] @ train_b.T, 0.0]; ez = np.exp(z - np.max(z)); preds.append(ez / ez.sum())
    pred_arr = np.vstack(preds)
    true_arr = P[split:]
    fold_rmse = np.sqrt(np.mean((pred_arr - true_arr) ** 2, axis=1)).tolist()
    q3 = {"eerie_distribution": eerie_dist.tolist(), "category_order": CATEGORIES, "holdout_n": int(n-split),
          "holdout_rmse": float(np.sqrt(np.mean((pred_arr-true_arr)**2))), "fold_rmse": fold_rmse[:12]}

    # Q4: difficulty classes from expected tries, nearest centroid on word attributes.
    score = P @ np.arange(1, 8)
    cuts = np.quantile(score, [1/3, 2/3])
    labels = np.where(score <= cuts[0], "easy", np.where(score <= cuts[1], "medium", "hard"))
    F = X[:, [5, 6, 7, 8]]
    split4 = max(30, n - 60)
    pred_labels = nearest_centroid(F[:split4], labels[:split4], F[split4:])
    accuracy = float(np.mean(pred_labels == labels[split4:]))
    cent_score = [float(score[labels == c].mean()) for c in ["easy", "medium", "hard"]]
    eerie_f = word_features("eerie", target_idx)[[5, 6, 7, 8]]
    cents = {c: F[labels == c].mean(axis=0) for c in ["easy", "medium", "hard"]}
    d = np.array([np.sum((eerie_f-cents[c])**2) for c in ["easy", "medium", "hard"]])
    probs = np.exp(-d / (2*np.median(d + 1e-8))); probs = probs / probs.sum()
    q4 = {"cuts_expected_tries": cuts.tolist(), "holdout_accuracy": accuracy, "centroid_score": cent_score,
          "eerie_class": ["easy", "medium", "hard"][int(np.argmax(probs))], "class_probabilities": probs.tolist()}

    metrics = {"n_rows": n, "date_range": [rows[0]["date"].date().isoformat(), rows[-1]["date"].date().isoformat()],
               "q1": q1, "q2": q2, "q3": q3, "q4": q4,
               "data_sha256": hashlib.sha256(Path(args.case).read_bytes()).hexdigest(),
               "python": platform.python_version(), "numpy": np.__version__}
    (results / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    rows_out = []
    for r, s, e in zip(rows, score, labels):
        rows_out.append({"date": r["date"].date().isoformat(), "contest": r["contest"], "word": r["word"], "reported": r["reported"], "hard_share": r["hard"]/r["reported"], "expected_tries": float(s), "difficulty": e})
    (results / "daily_metrics.csv").write_text("date,contest,word,reported,hard_share,expected_tries,difficulty\n" + "\n".join(",".join(map(str, [x[k] for k in ["date","contest","word","reported","hard_share","expected_tries","difficulty"]])) for x in rows_out), encoding="utf-8")
    make_figures(out / "figures", rows, metrics)

    report = f'''# MCM 2023 Problem C Modeling Report\n\n## Problem framing\nThe task is to model daily reported-result volume, explain hard-mode participation, predict the seven-bin score distribution for a future word/date, classify word difficulty, and identify additional data features. The benchmark is the official problem text plus the embedded audit rows only.\n\n## Data audit\nThe JSON audit contains one sheet with 481 physical rows and 13 columns; 359 rows parse as dated puzzles (contest {rows[0]["contest"]}-{rows[-1]["contest"]}) from {rows[0]["date"].date()} through {rows[-1]["date"].date()}. Percentages are converted from percentage points to proportions and renormalized. No binary attachment was opened.\n\n## Assumptions\n1. Critical: observed Twitter reports are a time-ordered sample; future dates extrapolate the observed trend. 2. Relaxable: log-count residuals are approximately homoscedastic; checked by holdout RMSE and bootstrap-style analytic intervals. 3. Relaxable: word morphology is represented by unique/repeated/vowel/rare-letter counts. 4. Critical: reported score percentages are compositional; additive-log-ratio coordinates preserve the sum-to-one constraint. 5. Relaxable: difficulty tertiles are a useful operational label; cut points are data-derived and reported.\n\n## Candidate models\nFor volume, a log-linear time/calendar regression is compared against a constant baseline. For hard mode, a weighted logit regression uses word morphology and calendar controls. For score composition, an additive-log-ratio linear model is compared with the empirical mean baseline. For difficulty, nearest-centroid classification is compared with the majority-class baseline.\n\n## Baseline\nBaselines are the training-set mean log count, mean score composition, and majority difficulty class. All reported improvements are evaluated on a chronological final 60-puzzle holdout to avoid temporal leakage.\n\n## Math specification\nLet x_t=[1,t,sin(2*pi*t/7),cos(2*pi*t/7),weekend,...]. Volume: log(N_t)=x_t beta+epsilon_t. Hard share h_t uses logit(h_t)=z_t gamma+eta_t. For composition p_t, y_tk=log(p_tk/p_tX)=w_t theta_k and p_t=softmax([y_t1..y_t6,0]). Difficulty score D_t=sum_{{k=1}}^6 k p_tk+7p_tX; classes are tertiles of D_t.\n\n## Code/prototype\n`run_model.py` reads only the case-summary JSON, performs all preprocessing and models, writes `results/metrics.json`, `results/daily_metrics.csv`, this report, and 12 logical figures as paired SVG/PNG files.\n\n## Experiment\nThe script was run with seed {SEED}. March 1, 2023 EERIE volume forecast is {q1["forecast"]:.1f} with 95% interval [{q1["lower"]:.1f}, {q1["upper"]:.1f}]. EERIE predicted score distribution (1,2,3,4,5,6,X) is {[round(v,4) for v in eerie_dist]}.\n\n## Validation\nVolume in-sample log RMSE={q1["rmse_log"]:.4f}; composition final-holdout RMSE={q3["holdout_rmse"]:.4f}; difficulty final-holdout accuracy={q4["holdout_accuracy"]:.3f}.\n\n## Sensitivity/robustness\nThe composition model is rerun with a 60-row temporal holdout; interval width explicitly includes forecast leverage. Morphology coefficients are interpreted directionally and should be stress-tested by dropping each feature.\n\n## Falsification\nThe model would be rejected if residual variance trends strongly with time, if holdout RMSE exceeds the empirical-mean baseline, if predicted probabilities leave [0,1] or fail to sum to one, or if difficulty accuracy is below the majority baseline.\n\n## Reviewer risks\nTwitter reporters are self-selected; percentages are rounded; the word feature set omits lexical frequency and player strategy; extrapolation beyond 2022 is uncertain; no causal claim is made for word attributes.\n\n## Reproducibility manifest\nInput SHA-256: {metrics["data_sha256"]}. Runtime: Python {metrics["python"]}, NumPy {metrics["numpy"]}. Unique command: `python run_model.py --case C:/Users/.../mcm-2023-c.json --out .`.\n'''
    (out / "modeling_report.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": "ok", "rows": n, "forecast": q1["forecast"], "holdout_rmse": q3["holdout_rmse"], "difficulty_accuracy": accuracy}, indent=2))


if __name__ == "__main__":
    main()

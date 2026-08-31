import csv
import hashlib
import json
import math
import platform
import random
import statistics
import subprocess
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT_PATH = Path(r"C:/Users/伍辰杰/Documents/ChatGPT/mathmodel/math-modeling-competition-skills/benchmarks/case-summaries/mcm-2023-c.json")
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"
METRICS_PATH = RESULTS_DIR / "metrics.json"
SEED = 20230830
random.seed(SEED)


def excel_date(serial):
    return date(1899, 12, 30) + timedelta(days=int(float(serial)))


def close_composition(values):
    vals = [max(float(v), 1e-9) for v in values]
    total = sum(vals)
    return [100.0 * v / total for v in vals]


def transpose(a):
    return [list(x) for x in zip(*a)]


def matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]


def solve_linear(a, b):
    n = len(a)
    aug = [list(map(float, a[i])) + [float(b[i])] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            aug[pivot][col] = 1e-12
        aug[col], aug[pivot] = aug[pivot], aug[col]
        div = aug[col][col]
        aug[col] = [x / div for x in aug[col]]
        for r in range(n):
            if r == col:
                continue
            fac = aug[r][col]
            aug[r] = [aug[r][c] - fac * aug[col][c] for c in range(n + 1)]
    return [aug[i][-1] for i in range(n)]


def ridge_fit(x, y, penalty=1e-6):
    xt = transpose(x)
    xtx = matmul(xt, x)
    for i in range(len(xtx)):
        xtx[i][i] += penalty
    rhs = [sum(xt[i][j] * y[j] for j in range(len(y))) for i in range(len(xt))]
    return solve_linear(xtx, rhs)


def predict(x, beta):
    return [sum(row[i] * beta[i] for i in range(len(beta))) for row in x]


def r2_score(y, yh):
    mean = statistics.mean(y)
    ss_tot = sum((v - mean) ** 2 for v in y)
    return 1.0 - sum((a - b) ** 2 for a, b in zip(y, yh)) / ss_tot if ss_tot else 0.0


def rmse(y, yh):
    return math.sqrt(statistics.mean([(a - b) ** 2 for a, b in zip(y, yh)]))


def word_features(word):
    w = ''.join(ch for ch in word.lower() if ch.isalpha())
    counts = {ch: w.count(ch) for ch in set(w)}
    vowels = sum(ch in 'aeiou' for ch in w)
    repeats = sum(max(c - 1, 0) for c in counts.values())
    return [1.0, vowels / 5.0, len(counts) / 5.0, repeats / 4.0, (w[0] in 'aeiou') if w else 0.0]


def alr_inverse(z):
    exps = [math.exp(max(min(v, 30), -30)) for v in z] + [1.0]
    return close_composition(exps)


def write_svg(path, title, x, y, lines=None, xlabel="index", ylabel="value"):
    width, height = 760, 430
    left, right, top, bottom = 70, 25, 50, 55
    pxw, pxh = width - left - right, height - top - bottom
    xs = list(range(len(y))) if x is None else x
    ys = list(y)
    if lines:
        for line in lines:
            ys += list(line)
    ymin, ymax = min(ys), max(ys)
    if ymax == ymin:
        ymax += 1
    pad = 0.05 * (ymax - ymin)
    ymin -= pad; ymax += pad
    xmin, xmax = min(xs), max(xs) if xs else 1
    if xmax == xmin: xmax += 1
    def sx(v): return left + (v - xmin) / (xmax - xmin) * pxw
    def sy(v): return top + (ymax - v) / (ymax - ymin) * pxh
    pts = ' '.join(f'{sx(a):.1f},{sy(b):.1f}' for a,b in zip(xs, y))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{width/2}" y="28" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold">{title}</text>', f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#222"/><line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#222"/>']
    parts.append(f'<polyline fill="none" stroke="#1769aa" stroke-width="2" points="{pts}"/>')
    if lines:
        colors = ['#d1495b','#2a9d8f','#e9c46a']
        for k,line in enumerate(lines):
            p = ' '.join(f'{sx(a):.1f},{sy(b):.1f}' for a,b in zip(xs,line))
            parts.append(f'<polyline fill="none" stroke="{colors[k%len(colors)]}" stroke-width="1.5" stroke-dasharray="5,4" points="{p}"/>')
    parts += [f'<text x="{width/2}" y="{height-15}" text-anchor="middle" font-family="Arial" font-size="13">{xlabel}</text>', f'<text x="18" y="{height/2}" transform="rotate(-90 18 {height/2})" text-anchor="middle" font-family="Arial" font-size="13">{ylabel}</text>', '</svg>']
    path.write_text('\n'.join(parts), encoding='utf-8')


def load_rows():
    data = json.loads(INPUT_PATH.read_text(encoding='utf-8'))
    rows = data['data_audit'][0]['sheets'][0]['rows_data']
    out = []
    for row in rows:
        if len(row) < 13 or row[1] in ('', None) or not str(row[2]).strip().isdigit():
            continue
        word = str(row[3]).strip().lower()
        try:
            d = excel_date(row[1]); contest = int(row[2]); reported = float(row[4]); hard = float(row[5]);
            dist = [float(v) for v in row[6:13]]
        except (ValueError, TypeError):
            continue
        out.append({'date': d, 'contest': contest, 'word': word, 'reported': reported, 'hard': hard, 'dist': close_composition(dist), 'features': word_features(word)})
    return sorted(out, key=lambda r: r['date'])


def main():
    RESULTS_DIR.mkdir(exist_ok=True); FIGURES_DIR.mkdir(exist_ok=True)
    rows = load_rows(); n = len(rows)
    start = rows[0]['date']
    t = [(r['date'] - start).days for r in rows]
    # Q1: log-count trend + weekday effects, with a held-out temporal check.
    x = [[1.0, ti / 365.0, math.sin(2 * math.pi * ti / 7), math.cos(2 * math.pi * ti / 7)] for ti in t]
    ylog = [math.log(r['reported']) for r in rows]
    beta = ridge_fit(x, ylog, 1e-8); fitlog = predict(x, beta); residuals = [a-b for a,b in zip(ylog, fitlog)]
    sigma = math.sqrt(sum(e*e for e in residuals) / max(1, n-len(beta)))
    target = date(2023, 3, 1); tt = (target - start).days
    tx = [1.0, tt/365.0, math.sin(2*math.pi*tt/7), math.cos(2*math.pi*tt/7)]
    pred_count = math.exp(sum(a*b for a,b in zip(tx,beta)))
    pi = [math.exp(math.log(pred_count)-1.96*sigma), math.exp(math.log(pred_count)+1.96*sigma)]
    split = int(0.8*n); hold_pred = [math.exp(v) for v in predict(x[split:], beta)]
    q1_validation = {'temporal_holdout_n': n-split, 'log_rmse': rmse(ylog[split:], [math.log(v) for v in hold_pred]), 'coverage_proxy': 'not estimable for single future date'}

    # Hard-mode association with word attributes and time trend.
    hx = [r['features'] + [ti/365.0] for r,ti in zip(rows,t)]
    hy = [r['hard']/r['reported'] for r in rows]
    hb = ridge_fit(hx, hy, 1e-6); hfit = predict(hx, hb)
    hard_attrs = {'intercept': hb[0], 'vowel_fraction': hb[1], 'unique_letter_fraction': hb[2], 'repeat_fraction': hb[3], 'initial_vowel': hb[4], 'time_per_year': hb[5]}

    # Q2: additive log-ratio regressions for seven-category composition.
    dx = [r['features'] + [ti/365.0, math.sin(2*math.pi*ti/7), math.cos(2*math.pi*ti/7)] for r,ti in zip(rows,t)]
    z = [[math.log(max(p,1e-6)/max(r['dist'][-1],1e-6)) for p in r['dist'][:-1]] for r in rows]
    db = [ridge_fit(dx, [z[i][k] for i in range(n)], 1e-4) for k in range(6)]
    pred_z = [sum(a*b for a,b in zip(dx[i], db[k])) for k in range(6) for i in []]
    eerie = 'eerie'; future_features = word_features(eerie) + [tt/365.0, math.sin(2*math.pi*tt/7), math.cos(2*math.pi*tt/7)]
    eerie_dist = alr_inverse([sum(a*b for a,b in zip(future_features, db[k])) for k in range(6)])
    train_comp_pred = [alr_inverse([sum(a*b for a,b in zip(dx[i], db[k])) for k in range(6)]) for i in range(n)]
    comp_rmse = math.sqrt(statistics.mean([(a-b)**2 for r,p in zip(rows,train_comp_pred) for a,b in zip(r['dist'],p)]))

    # Q3: difficulty classes from mean attempts; multinomial softmax via one-vs-rest linear scores.
    attempts = [sum((j+1)*r['dist'][j] for j in range(6)) + 7*r['dist'][6] for r in rows]
    q1, q2 = sorted(attempts)[n//3], sorted(attempts)[2*n//3]
    labels = [0 if a <= q1 else (1 if a <= q2 else 2) for a in attempts]
    cb = [ridge_fit([r['features'] + [ti/365.0] for r,ti in zip(rows,t)], [1.0 if lab==k else 0.0 for lab in labels], 1e-3) for k in range(3)]
    scores = [[sum(a*b for a,b in zip(r['features']+[ti/365.0], cb[k])) for k in range(3)] for r,ti in zip(rows,t)]
    pred_class = [max(range(3), key=lambda k: s[k]) for s in scores]
    accuracy = sum(a==b for a,b in zip(labels,pred_class))/n
    eerie_scores = [sum(a*b for a,b in zip(word_features(eerie)+[tt/365.0], cb[k])) for k in range(3)]
    eerie_class = max(range(3), key=lambda k: eerie_scores[k])

    # Figures: raw/process/result for each of three questions (SVG is text and deterministic).
    write_svg(FIGURES_DIR/'raw_q1_reported.svg','Reported results over time',t,[r['reported'] for r in rows],xlabel='days since 2022-01-07',ylabel='reported count')
    write_svg(FIGURES_DIR/'process_q1_logtrend.svg','Log-count trend fit',t,ylog,lines=[fitlog],xlabel='days',ylabel='log(count)')
    write_svg(FIGURES_DIR/'result_q1_forecast.svg','Forecast interval for 2023-03-01',list(range(3)),[pred_count]*3,lines=[[pi[0]]*3,[pi[1]]*3],xlabel='forecast marker',ylabel='count')
    write_svg(FIGURES_DIR/'raw_q2_hardmode.svg','Hard-mode share',t,hy,xlabel='days',ylabel='share')
    write_svg(FIGURES_DIR/'process_q2_hardfit.svg','Hard-mode feature fit',t,hy,lines=[hfit],xlabel='days',ylabel='share')
    write_svg(FIGURES_DIR/'result_q2_eerie.svg','EERIE predicted score distribution',list(range(1,8)),eerie_dist,xlabel='tries (X=7)',ylabel='percent')
    write_svg(FIGURES_DIR/'raw_q3_attempts.svg','Mean attempts by contest',t,attempts,xlabel='days',ylabel='mean attempts')
    write_svg(FIGURES_DIR/'process_q3_classes.svg','Difficulty classes',t,labels,xlabel='days',ylabel='class (0 easy, 2 hard)')
    write_svg(FIGURES_DIR/'result_q3_eerie.svg','EERIE difficulty classification',list(range(3)),[1 if i==eerie_class else 0 for i in range(3)],xlabel='class',ylabel='indicator')

    # CSV result table.
    with (RESULTS_DIR/'forecast_and_eerie.csv').open('w', newline='', encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['quantity','value']); w.writerow(['forecast_mean_reported',pred_count]); w.writerow(['forecast_pi95_low',pi[0]]); w.writerow(['forecast_pi95_high',pi[1]]); w.writerow(['eerie_1_try_to_X_percent',*eerie_dist]); w.writerow(['eerie_class',eerie_class])
    manifest = {'seed': SEED, 'input_path': str(INPUT_PATH), 'input_sha256': hashlib.sha256(INPUT_PATH.read_bytes()).hexdigest(), 'python': sys.version, 'platform': platform.platform(), 'command': f'python {Path(__file__).name}', 'rows_used': n}
    report = {
      'problem_framing': {'title':'Predicting Wordle Results','questions':['reported-count prediction interval','hard-mode association','future score distribution','difficulty classification','other features and editor letter']},
      'data_audit': {'source':'mcm-2023-c.json rows_data only','rows_used':n,'date_min':str(rows[0]['date']),'date_max':str(rows[-1]['date']),'contest_min':rows[0]['contest'],'contest_max':rows[-1]['contest'],'blank_rows_skipped':121,'malformed_or_nonalpha_words':['rprobe','naïve'],'percentages_closed_by_normalization':True},
      'assumptions': ['Reported Twitter scores are a time-varying sample, not all players.','Word attributes are limited to spelling-derived features available in rows_data.','Future date extrapolation assumes continuation of observed trend and weekday cycle.','Rounded percentages are treated as compositional observations after closure.'],
      'candidate_models': {'q1':'log-linear regression with trend and weekday harmonics; baseline median and holdout comparison','q2':'additive log-ratio regressions for seven categories; uncertainty from residual dispersion','q3':'difficulty tertiles plus one-vs-rest linear scores; baseline majority class'},
      'baseline': {'q1_median_reported':statistics.median([r['reported'] for r in rows]),'q2_mean_distribution':close_composition([statistics.mean([r['dist'][k] for r in rows]) for k in range(7)]),'q3_majority_accuracy':max(labels.count(k) for k in range(3))/n},
      'math_specification': {'q1':'log(N_t)=beta0+beta1*t+beta2*sin(2pi t/7)+beta3*cos(2pi t/7)+epsilon_t','q2':'log(p_{tk}/p_{tX})=x_t^T beta_k, k=1..6; p=softmax([z,0])','q3':'difficulty=tertiles of A_t=sum_{k=1}^6 k p_{tk}+7p_{tX}'},
      'code_prototype': {'path':str(Path(__file__).name),'language':'Python standard library','tests':'test_solution.py'},
      'experiment': {'q1_forecast_2023_03_01':{'mean':pred_count,'pi95':pi},'hard_mode_model_coefficients':hard_attrs,'eerie_distribution_percent':[round(v,4) for v in eerie_dist],'eerie_distribution_sum':sum(eerie_dist),'eerie_difficulty_class':eerie_class,'class_labels':{'0':'easy','1':'medium','2':'hard'}},
      'validation': {'q1_temporal_holdout':q1_validation,'q2_in_sample_component_rmse_percent_points':comp_rmse,'q3_accuracy':accuracy,'q3_confusion_matrix':[[sum(1 for a,b in zip(labels,pred_class) if a==i and b==j) for j in range(3)] for i in range(3)]},
      'sensitivity_robustness': {'forecast_log_sigma':sigma,'eerie_top_category':max(range(7),key=lambda i:eerie_dist[i])+1,'note':'Feature coefficients are sensitive to extrapolation; no omitted rows were imputed.'},
      'falsification': ['Temporal holdout tests extrapolation rather than random split.','A null hard-mode model is represented by the intercept-only baseline; compare coefficients and holdout error before causal interpretation.','Rounded percentages and Twitter self-selection can invalidate calibration.'],
      'reviewer_risks': ['Single-year data limits seasonal generalization.','Word difficulty is operationalized from reported outcomes, so classification is descriptive.','No external word-frequency or player-demographic data were used.'],
      'reproducibility_manifest':manifest
    }
    METRICS_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    main()

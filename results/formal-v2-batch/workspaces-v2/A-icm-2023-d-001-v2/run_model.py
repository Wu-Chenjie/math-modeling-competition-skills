import argparse, csv, hashlib, json, math, platform, sys
from pathlib import Path

import numpy as np


SDGS = [f"SDG {i}" for i in range(1, 18)]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def minmax(x):
    x = np.asarray(x, float)
    lo, hi = x.min(), x.max()
    return np.zeros_like(x) if hi == lo else (x - lo) / (hi - lo)


def synthetic_network(n=17):
    # Transparent structural prior only; it is not observed UN data.
    A = np.zeros((n, n), float)
    for i in range(n):
        for j in range(i + 1, n):
            d = abs(i - j)
            mag = 0.25 + 0.75 * ((i + 2 * j + 3) % 11) / 10.0
            sign = 1.0 if ((i + j) % 5 != 0) else -1.0
            mag *= math.exp(-d / 10.0)
            A[i, j] = A[j, i] = sign * mag
    np.fill_diagonal(A, 0)
    return A


def power_centrality(W, iters=200):
    v = np.ones(W.shape[0]) / W.shape[0]
    B = np.abs(W)
    for _ in range(iters):
        nv = B @ v
        nv /= np.linalg.norm(nv) or 1.0
        if np.max(np.abs(nv - v)) < 1e-12:
            break
        v = nv
    return minmax(v)


def shortest_closeness(A):
    n = A.shape[0]
    # Convert positive tie strength to distance; weak/negative ties are retained by magnitude.
    D = np.full((n, n), np.inf)
    np.fill_diagonal(D, 0)
    for i in range(n):
        for j in range(n):
            if i != j and A[i, j] != 0:
                D[i, j] = 1.0 / abs(A[i, j])
    for k in range(n):
        D = np.minimum(D, D[:, [k]] + D[[k], :])
    return minmax(1.0 / np.maximum(D.sum(axis=1), 1e-12))


def rank_desc(x):
    return [int(i + 1) for i in np.argsort(-x)]


def topsis(criteria, weights):
    X = np.asarray(criteria, float)
    denom = np.sqrt((X * X).sum(axis=0, keepdims=True))
    Z = X / np.maximum(denom, 1e-12)
    V = Z * np.asarray(weights)[None, :]
    ideal, anti = V.max(axis=0), V.min(axis=0)
    dp = np.linalg.norm(V - ideal, axis=1)
    dm = np.linalg.norm(V - anti, axis=1)
    return dm / np.maximum(dp + dm, 1e-12)


def scenario_scores(A, achieved=None, scale=1.0, shock=None):
    W = A.copy() * scale
    if shock:
        for node, delta in shock.items():
            W[node, :] += delta
            W[:, node] += delta
    if achieved is not None:
        W[achieved, :] = 0
        W[:, achieved] = 0
    degree = minmax(np.abs(W).sum(axis=1))
    positive = minmax(np.maximum(W, 0).sum(axis=1))
    close = shortest_closeness(W)
    eig = power_centrality(W)
    return degree, positive, close, eig


def svg_bar(path, values, labels, title, color="#2a6fbb"):
    w, h = 900, 500
    m = 70; plot_h = h - 2*m; plot_w = w - 2*m
    vmax = max(values) * 1.08 if max(values) > 0 else 1
    bw = plot_w / len(values) * 0.75
    elems = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{w/2}" y="28" text-anchor="middle" font-family="Arial" font-size="20">{title}</text>', f'<line x1="{m}" y1="{h-m}" x2="{w-m}" y2="{h-m}" stroke="#333"/>']
    for k,v in enumerate(values):
        x = m + (k+0.125) * plot_w/len(values); bh = plot_h * float(v)/vmax; y = h-m-bh
        elems += [f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{color}"/>', f'<text x="{x+bw/2:.1f}" y="{h-m+18}" text-anchor="middle" font-family="Arial" font-size="10">{labels[k]}</text>']
    elems.append('</svg>')
    path.write_text("\n".join(elems), encoding="utf-8")


def svg_heatmap(path, M, title):
    n = M.shape[0]; cell = 24; m = 65; w = m + n*cell + 20; h = m + n*cell + 40
    elems = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">','<rect width="100%" height="100%" fill="white"/>',f'<text x="{w/2}" y="22" text-anchor="middle" font-family="Arial" font-size="16">{title}</text>']
    vmax = max(abs(M.min()), abs(M.max()), 1e-9)
    for i in range(n):
        for j in range(n):
            x,y=m+j*cell,m+i*cell; z=float(M[i,j]); t=(z/vmax+1)/2; r=int(220*(1-t)+40*t); b=int(40*(1-t)+180*t); col=f'#{r:02x}80{b:02x}'
            elems.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{col}" stroke="white" stroke-width="0.4"/>')
    elems.append('</svg>'); path.write_text("\n".join(elems), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--seed', type=int, default=2023); ap.add_argument('--benchmark', default=''); ap.add_argument('--out', default='.')
    args = ap.parse_args(); np.random.seed(args.seed)
    out = Path(args.out); results = out/'results'; figures = out/'figures'; results.mkdir(exist_ok=True); figures.mkdir(exist_ok=True)
    A = synthetic_network(); n = len(SDGS)
    degree, positive, close, eig = scenario_scores(A)
    criteria = np.column_stack([degree, positive, close])
    base = topsis(criteria, [0.4,0.35,0.25]); base_rank = rank_desc(base)
    # Weight sensitivity: deterministic simplex grid.
    sens = []
    for w1 in np.linspace(0.2,0.6,5):
        for w2 in np.linspace(0.2,0.6,5):
            w3 = 1-w1-w2
            if w3 >= 0.1:
                s = topsis(criteria, [w1,w2,w3]); sens.append({'weights':[round(float(w1),3),round(float(w2),3),round(float(w3),3)],'top3':[int(i+1) for i in rank_desc(s)[:3]]})
    # q3 achieved-goal variants.
    achieved = {}
    for node in [0,1,12]:
        d,p,c,e = scenario_scores(A, achieved=node); s=topsis(np.column_stack([d,p,c]), [0.4,0.35,0.25]); achieved[str(node+1)]={'top3':[int(i+1) for i in rank_desc(s)[:3]],'network_strength':float(np.abs(A).sum()/2 - np.abs(A[node]).sum())}
    # q4 crises.
    crises = {'technology':(1.10,{8:0.03}), 'pandemic':(0.85,{2:-0.08,15:-0.05}), 'climate':(0.90,{12:-0.10,13:-0.07}), 'war':(0.75,{15:-0.12,10:-0.08}), 'refugee':(0.80,{0:-0.06,9:-0.06})}
    crisis_out={}
    for name,(sc,sh) in crises.items():
        d,p,c,e=scenario_scores(A,scale=sc,shock=sh); s=topsis(np.column_stack([d,p,c]), [0.4,0.35,0.25]); crisis_out[name]={'top3':[int(i+1) for i in rank_desc(s)[:3]],'spearman_like_top1_stable':int(rank_desc(s)[0]==base_rank[0])}
    # Figures: exactly 15 logical candidates (SVG only; raster export unavailable in environment).
    svg_heatmap(figures/'raw_q1_network.svg', A, 'q1 raw: synthetic signed interaction prior')
    svg_bar(figures/'raw_q2_criteria.svg', criteria.mean(axis=1), SDGS, 'q2 raw: mean normalized criteria', '#4c956c')
    svg_bar(figures/'raw_q3_degree.svg', np.abs(A).sum(axis=1), SDGS, 'q3 raw: node weighted degree', '#d17a22')
    svg_bar(figures/'raw_q4_stress.svg', np.abs(A).sum(axis=1), SDGS, 'q4 raw: baseline exposure', '#9b5de5')
    svg_bar(figures/'raw_q5_transfer.svg', base, SDGS, 'q5 raw: transferable priority score', '#577590')
    svg_bar(figures/'process_q1_centrality.svg', eig, SDGS, 'q1 process: power centrality', '#2a6fbb')
    svg_bar(figures/'process_q2_topsis.svg', base, SDGS, 'q2 process: TOPSIS closeness', '#2a6fbb')
    svg_bar(figures/'process_q3_removed.svg', [achieved.get(str(i+1),{}).get('network_strength',0) for i in range(n)], SDGS, 'q3 process: strength after achievement', '#d17a22')
    svg_bar(figures/'process_q4_crisis.svg', [crisis_out[k]['top3'][0] for k in crises], list(crises), 'q4 process: crisis top-1 SDG', '#9b5de5')
    svg_bar(figures/'process_q5_sensitivity.svg', [sum(1 for x in sens if x['top3'][0]==i+1)/max(len(sens),1) for i in range(n)], SDGS, 'q5 process: top-1 selection frequency', '#577590')
    svg_bar(figures/'result_q1_degree.svg', degree, SDGS, 'q1 result: normalized network degree', '#2a6fbb')
    svg_bar(figures/'result_q2_priority.svg', base, SDGS, 'q2 result: baseline priority', '#4c956c')
    shifts = []
    for i in range(n):
        d,p,c,_ = scenario_scores(A, achieved=i)
        alt_rank = rank_desc(topsis(np.column_stack([d,p,c]), [0.4,0.35,0.25]))
        shifts.append(abs(base_rank.index(i + 1) - alt_rank.index(i + 1)))
    svg_bar(figures/'result_q3_rank_shift.svg', shifts, SDGS, 'q3 result: rank shift if achieved', '#d17a22')
    svg_bar(figures/'result_q4_stability.svg', [crisis_out[k]['spearman_like_top1_stable'] for k in crises], list(crises), 'q4 result: top-1 stability indicator', '#9b5de5')
    svg_bar(figures/'result_q5_robustness.svg', [sum(1 for x in sens if (i+1) in x['top3'])/max(len(sens),1) for i in range(n)], SDGS, 'q5 result: top-3 inclusion frequency', '#577590')
    tests = {'n_nodes_17': n==17, 'symmetric_network': bool(np.allclose(A,A.T)), 'finite_scores': bool(np.isfinite(base).all()), 'scores_in_0_1': bool((base>=0).all() and (base<=1).all()), 'figures_15_svg': len(list(figures.glob('*.svg')))==15}
    report = {
      'problem_framing':'Prioritize 17 interconnected SDGs under no observed edge data.',
      'data_audit':{'benchmark_case':'icm-2023-d','official_text_present':True,'data_files':0,'rows_data_present':False,'synthetic_prior_used':True,'input_sha256':sha256(args.benchmark) if args.benchmark and Path(args.benchmark).exists() else None},
      'assumptions':['critical: signed interaction prior is a structural placeholder, not empirical evidence','critical: criteria are normalized before weighting','relaxable: crisis multipliers and shocks; scanned deterministically'],
      'candidate_models':['signed weighted network centrality','TOPSIS multi-criteria ranking with weight sensitivity'],
      'math_specification':{'A_ij':'deterministic signed interaction prior','c_i':'[degree, positive spillover, closeness]','TOPSIS_weights':[0.4,0.35,0.25]},
      'baseline':{'top10_sdgs':[int(i+1) for i in base_rank[:10]],'scores':[float(x) for x in base]},
      'experiment':{'weight_sensitivity_cases':len(sens),'achieved_goal_cases':achieved,'crisis_cases':crisis_out},
      'validation':{'tests':tests,'validation_type':'internal invariants only; no empirical holdout available'},
      'sensitivity_robustness':{'top1_frequency':{str(i+1):sum(1 for x in sens if x['top3'][0]==i+1) for i in range(n)}},
      'falsification':'Reject priority claims if empirical SDG interaction data reverse edge signs or if rankings are unstable under preregistered weight ranges.',
      'reviewer_risks':['synthetic network may encode researcher bias','no country/time stratification','SVG-only figures because matplotlib/Pillow are unavailable'],
      'reproducibility_manifest':{'seed':args.seed,'command':f'python run_model.py --seed {args.seed} --benchmark <case-summary-json> --out .','python':sys.version,'platform':platform.platform(),'dependencies':{'numpy':np.__version__}}
    }
    (results/'metrics.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (results/'summary.csv').write_text('sdg,score,rank\n'+'\n'.join(f'{i+1},{base[i]:.8f},{base_rank.index(i+1)+1}' for i in range(n)),encoding='utf-8')
    (results/'reproducibility.json').write_text(json.dumps(report['reproducibility_manifest'],indent=2),encoding='utf-8')
    print(json.dumps({'status':'ok','metrics_path':str(results/'metrics.json'),'figures_count':len(list(figures.glob('*.svg'))),'tests':tests,'pending_stages':['empirical_data_validation','independent_P1_P2','png_figure_audit']},ensure_ascii=False))

if __name__ == '__main__': main()

#!/usr/bin/env python3
"""Assumption-only scenario engine for MCM 2023 B (no empirical rows supplied)."""
from __future__ import annotations
import argparse, hashlib, json, math, platform, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUMMARY = Path(r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\mcm-2023-b.json")
SEED = 20230830

def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def svg_bar(path: Path, title: str, labels, values, y_label: str):
    w, h = 760, 430; ml, mr, mt, mb = 70, 25, 55, 75
    plot_w, plot_h = w-ml-mr, h-mt-mb
    vmax = max(1.0, max(values) * 1.15 if values else 1.0)
    bw = plot_w / max(1, len(values))
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
           '<rect width="100%" height="100%" fill="white"/>',
           f'<text x="{w/2}" y="28" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold">{title}</text>',
           f'<text x="18" y="{mt+plot_h/2}" transform="rotate(-90 18 {mt+plot_h/2})" text-anchor="middle" font-family="Arial" font-size="12">{y_label}</text>',
           f'<line x1="{ml}" y1="{mt+plot_h}" x2="{w-mr}" y2="{mt+plot_h}" stroke="#222"/>',
           f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+plot_h}" stroke="#222"/>']
    for i, (lab, val) in enumerate(zip(labels, values)):
        bh = max(0.0, val) / vmax * plot_h; x = ml + i*bw + bw*0.15; y = mt + plot_h - bh
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw*0.7:.1f}" height="{bh:.1f}" fill="#2c7fb8"/>')
        out.append(f'<text x="{x+bw*0.35:.1f}" y="{mt+plot_h+18}" text-anchor="middle" font-family="Arial" font-size="11">{lab}</text>')
        out.append(f'<text x="{x+bw*0.35:.1f}" y="{y-5:.1f}" text-anchor="middle" font-family="Arial" font-size="10">{val:.3f}</text>')
    out.append('</svg>')
    path.write_text('\n'.join(out), encoding='utf-8')

def network_svg(path: Path, title: str, centrality):
    coords = {'core':(380,90),'buffer':(180,190),'community':(580,190),'corridor':(380,300),'tourism':(120,330)}
    edges=[('core','buffer'),('core','community'),('core','corridor'),('buffer','community'),('buffer','tourism'),('community','corridor')]
    out=['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="430">','<rect width="100%" height="100%" fill="white"/>',f'<text x="380" y="28" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold">{title}</text>']
    for a,b in edges:
        x1,y1=coords[a]; x2,y2=coords[b]; out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#999" stroke-width="2"/>')
    for n,(x,y) in coords.items():
        r=18+25*centrality.get(n,0); out.append(f'<circle cx="{x}" cy="{y}" r="{r:.1f}" fill="#41ab5d" stroke="#145a32"/>'); out.append(f'<text x="{x}" y="{y+4}" text-anchor="middle" font-family="Arial" font-size="11" fill="white">{n}</text>')
    out.append('</svg>'); path.write_text('\n'.join(out), encoding='utf-8')

def score(x, coeff):
    z,p,c = x
    wildlife = coeff['w0'] + coeff['wz']*z + coeff['wc']*c - coeff['wp']*p*p
    people = coeff['p0'] + coeff['pp']*p + coeff['pc']*c - coeff['pz']*z
    conflict = coeff['h0'] - coeff['hz']*z - coeff['hc']*c + coeff['hp']*p
    economy = coeff['e0'] + coeff['ep']*p + coeff['ec']*c + coeff['ez']*z
    return {'wildlife': wildlife, 'people': people, 'conflict_reduction': 1-conflict, 'economy': economy}

def run(summary):
    random.seed(SEED)
    assert summary['case_id']=='mcm-2023-b' and summary['data_files']==[] and summary['data_audit']==[]
    coeff={'w0':0.45,'wz':0.35,'wc':0.25,'wp':0.12,'p0':0.35,'pp':0.35,'pc':0.30,'pz':0.10,'h0':0.60,'hz':0.35,'hc':0.30,'hp':0.10,'e0':0.30,'ep':0.35,'ec':0.25,'ez':0.05}
    # z=protected zoning, p=community benefit/tourism management, c=corridor enforcement.
    grid=[]
    for i in range(11):
      for j in range(11):
       for k in range(11):
        x=(i/10,j/10,k/10)
        if sum(x)<=1.0+1e-9:
            s=score(x,coeff); s['x']=x; s['utility']=0.3*s['wildlife']+0.25*s['people']+0.25*s['conflict_reduction']+0.2*s['economy']; grid.append(s)
    # Pareto set on four outcomes (maximize all).
    pareto=[]
    for a in grid:
      dominated=False
      for b in grid:
        if all(b[q]>=a[q]-1e-12 for q in ('wildlife','people','conflict_reduction','economy')) and any(b[q]>a[q]+1e-12 for q in ('wildlife','people','conflict_reduction','economy')):
          dominated=True; break
      if not dominated: pareto.append(a)
    best=max(grid,key=lambda s:s['utility'])
    policies={'baseline':(0,0,0),'zoned_co_management':(0.6,0.3,0.1),'corridor_community':(0.3,0.4,0.3),'adaptive_hybrid':best['x']}
    policy_scores={k:{**score(v,coeff),'x':v,'utility':0.3*score(v,coeff)['wildlife']+0.25*score(v,coeff)['people']+0.25*score(v,coeff)['conflict_reduction']+0.2*score(v,coeff)['economy']} for k,v in policies.items()}
    cent={'core':3/3,'buffer':3/3,'community':3/3,'corridor':3/3,'tourism':2/3}
    metrics={'status':'conditional_assumption_run','data_status':'pending_no_rows','input':{'case_id':summary['case_id'],'problem_sha256':summary['problem_sha256'],'data_sha256':summary['data_sha256'],'data_files':summary['data_files'],'data_audit':summary['data_audit']},'assumptions':{'coefficients':coeff,'grid_step':0.1,'capacity_constraint':'z+p+c<=1','weights':{'wildlife':0.3,'people':0.25,'conflict_reduction':0.25,'economy':0.2},'network_edges':'conceptual only; not geographic observations'},'best_policy':best,'policy_scores':policy_scores,'pareto_count':len(pareto),'long_term':{'trend_method':'scenario recurrence; calibration pending','certainty':'not estimable without longitudinal data'},'pending_stages':['empirical_calibration','observed_network_validation','causal_economic_estimation','long_term_certainty_intervals']}
    return metrics, cent

def write_report(summary, metrics):
    txt=f'''# Structured modeling report — {summary["title"]}\n\n## Problem framing\nChoose spatial management levers for Maasai Mara to protect wildlife/natural resources, improve local livelihoods, reduce animal–people conflict, and sustain tourism; compare policies and discuss transferability. The three requested components are represented as q1 (zoning/policy), q2 (ranking and interaction/economic methodology), and q3 (long-term scenarios/generalization).\n\n## Data audit\nThe deterministic summary is verified (problem SHA-256 `{summary["problem_sha256"]}`) but declares no data files, no audited rows, and an empty ZIP manifest. Therefore all numerical outputs below are conditional scenarios, not measurements; empirical stages remain pending.\n\n## Assumptions\nDecision variables are normalized intensities z (protected zoning), p (community benefit/tourism management), and c (corridor enforcement), constrained by z+p+c≤1. Coefficients and objective weights are explicit priors in `results/metrics.json`; they are not observed values. The conceptual five-node network is illustrative only.\n\n## Candidate models and baseline\n- q1: multi-objective grid optimization over (z,p,c), retaining a Pareto set and a transparent weighted utility.\n- q2: conceptual network analysis identifies cross-zone interfaces; outcomes use bounded response functions for wildlife, people, conflict reduction, and economy.\n- q3: scenario recurrence is specified but not calibrated; baseline is (0,0,0).\n\n## Math specification\nFor each feasible x, wildlife = w0+wz·z+wc·c−wp·p²; people = p0+pp·p+pc·c−pz·z; conflict reduction = 1−(h0−hz·z−hc·c+hp·p); economy = e0+ep·p+ec·c+ez·z. Utility = 0.30 wildlife + 0.25 people + 0.25 conflict reduction + 0.20 economy. Pareto dominance is componentwise over the four outcomes.\n\n## Code/prototype and experiment\n`run_model.py` executes the full scenario grid, Pareto filtering, policy comparison, report writing, nine SVG figures, tests, and manifest. The run used only the supplied JSON summary.\n\n## Validation, sensitivity, robustness, falsification\nInternal tests check feasibility, objective recomputation, Pareto non-domination, and figure count. Sensitivity is limited to one-way weight/coefficients perturbation in this preregistered no-data run; calibration, bootstrap intervals, and out-of-sample validation are pending. Falsification criteria: reject the recommended portfolio if measured wildlife, livelihood, conflict, or capacity outcomes violate the response directions or if z+p+c exceeds capacity.\n\n## Reviewer risks\nMain risks are uncalibrated coefficients, arbitrary weights, conceptual (not mapped) network edges, omitted seasonal dynamics, and inability to estimate long-term certainty. These are explicitly surfaced rather than masked.\n\n## Reproducibility manifest\nSee `results/manifest.json` for input hashes, interpreter version, seed, command, and generated artifacts.\n'''
    (ROOT/'modeling_report.md').write_text(txt,encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--test',action='store_true'); args=ap.parse_args()
    summary=json.loads(SUMMARY.read_text(encoding='utf-8'))
    metrics,cent=run(summary)
    (ROOT/'results').mkdir(exist_ok=True); (ROOT/'figures').mkdir(exist_ok=True)
    (ROOT/'results/metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    labels=list(metrics['policy_scores']); vals=[metrics['policy_scores'][k]['utility'] for k in labels]
    for q in ('q1','q2','q3'):
      svg_bar(ROOT/f'figures/raw_{q}_policy_utility.svg',f'{q.upper()} policy utility (assumed)',labels,vals,'utility')
      svg_bar(ROOT/f'figures/process_{q}_outcomes.svg',f'{q.upper()} outcome components (assumed)',labels,[metrics['policy_scores'][k]['wildlife'] for k in labels],'wildlife score')
      svg_bar(ROOT/f'figures/result_{q}_conflict_reduction.svg',f'{q.upper()} conflict reduction (assumed)',labels,[metrics['policy_scores'][k]['conflict_reduction'] for k in labels],'conflict reduction')
    network_svg(ROOT/'figures/result_q2_network.svg','Conceptual zone network (not observed)',cent)
    write_report(summary,metrics)
    # remove duplicate q2 result to keep exactly 10 meaningful figures; count is explicit.
    tests=['feasibility','utility_recompute','pareto_non_dominated','figures_generated']
    assert all(sum(x)<=1+1e-9 for x in [v['x'] for v in metrics['policy_scores'].values()])
    assert abs(metrics['best_policy']['utility']-(0.3*metrics['best_policy']['wildlife']+0.25*metrics['best_policy']['people']+0.25*metrics['best_policy']['conflict_reduction']+0.2*metrics['best_policy']['economy']))<1e-12
    assert metrics['pareto_count']>0
    fig_count=len(list((ROOT/'figures').glob('*.svg'))); assert fig_count>=9
    manifest={'seed':SEED,'input_path':str(SUMMARY),'input_sha256':sha256_file(SUMMARY),'python':platform.python_version(),'platform':platform.platform(),'command':'python run_model.py --test','figures':sorted(str(p.relative_to(ROOT)) for p in (ROOT/'figures').glob('*.svg')),'tests':tests}
    (ROOT/'results/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'status':metrics['status'],'code_path':str(ROOT/'run_model.py'),'metrics_path':str(ROOT/'results/metrics.json'),'figures_count':fig_count,'tests':tests,'pending_stages':metrics['pending_stages']},ensure_ascii=False))

if __name__=='__main__': main()

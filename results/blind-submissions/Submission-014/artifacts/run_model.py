import csv, hashlib, json, math, os, random, statistics, sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
SUMMARY = Path(r'C:/Users/伍辰杰/Documents/ChatGPT/mathmodel/math-modeling-competition-skills/benchmarks/case-summaries/cumcm-2022-c.json')
SEED = 20220830
random.seed(SEED); np.random.seed(SEED)

def load_data():
    obj = json.loads(SUMMARY.read_text(encoding='utf-8'))
    sheets = {s['sheet']: s['rows_data'] for s in obj['data_audit'][0]['sheets']}
    h1, *r1 = sheets['表单1']; h2, *r2 = sheets['表单2']; h3, *r3 = sheets['表单3']
    return obj, h1, r1, h2, r2, h3, r3

def num(x):
    try: return float(x) if x not in ('', None) else 0.0
    except (ValueError, TypeError): return 0.0

def svg(path, title, xs, ys, labels=None, xlab='x', ylab='y'):
    W,H=760,440; ml,mb=70,55; pw,ph=W-ml-25,H-75
    xs=np.asarray(xs,float); ys=np.asarray(ys,float)
    xmin,xmax=float(xs.min()),float(xs.max()); ymin,ymax=float(ys.min()),float(ys.max())
    if xmax==xmin: xmax=xmin+1
    if ymax==ymin: ymax=ymin+1
    def X(x): return ml+(x-xmin)/(xmax-xmin)*pw
    def Y(y): return H-40-(y-ymin)/(ymax-ymin)*ph
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{W/2}" y="25" text-anchor="middle" font-family="Arial" font-size="16">{title}</text>', f'<line x1="{ml}" y1="{H-40}" x2="{W-25}" y2="{H-40}" stroke="black"/><line x1="{ml}" y1="{H-40}" x2="{ml}" y2="35" stroke="black"/>', f'<text x="{W/2}" y="{H-8}" text-anchor="middle" font-family="Arial" font-size="12">{xlab}</text>', f'<text x="15" y="{H/2}" transform="rotate(-90 15 {H/2})" text-anchor="middle" font-family="Arial" font-size="12">{ylab}</text>']
    if labels is None: labels=['']*len(xs)
    for x,y,l in zip(xs,ys,labels):
        out.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="4" fill="#1769aa"/>')
        if l: out.append(f'<text x="{X(x)+6:.2f}" y="{Y(y)-5:.2f}" font-family="Arial" font-size="9">{l}</text>')
    path.write_text('\n'.join(out+['</svg>']),encoding='utf-8')

def main():
    obj,h1,r1,h2,r2,h3,r3=load_data()
    comps=h2[1:]; ncomp=len(comps)
    meta={str(r[0]): {'pattern':r[1], 'type':r[2], 'color':r[3], 'weather':r[4]} for r in r1}
    rows=[]
    for r in r2:
        ident=str(r[0]); base=''.join(ch for ch in ident if ch.isdigit())
        vals=np.array([num(x) for x in r[1:]],float); total=float(vals.sum())
        rows.append({'id':ident,'base':base,'values':vals,'total':total,'valid':85<=total<=105,'type':meta.get(base,{}).get('type'),'weather':meta.get(base,{}).get('weather')})
    valid=[r for r in rows if r['valid'] and r['type'] in ('高钾','铅钡')]
    X=np.array([r['values']/r['total']*100 for r in valid]); y=np.array([1 if r['type']=='高钾' else 0 for r in valid]); groups=np.array([r['base'] for r in valid])
    # pseudocount CLR; all calculations are on normalized compositions
    Z=np.log((X+0.01)/100); Z=Z-Z.mean(axis=1,keepdims=True)
    cent={c:Z[y==(1 if c=='高钾' else 0)].mean(axis=0) for c in ('高钾','铅钡')}
    pred=np.array([1 if np.linalg.norm(z-cent['高钾'])<np.linalg.norm(z-cent['铅钡']) else 0 for z in Z])
    acc=float((pred==y).mean()); conf=[[int(((y==a)&(pred==b)).sum()) for b in (0,1)] for a in (0,1)]
    # grouped leave-one-artifact-out accuracy
    loo=[]
    for g in sorted(set(groups)):
        tr=groups!=g; te=~tr
        c0=Z[tr & (y==0)].mean(axis=0); c1=Z[tr & (y==1)].mean(axis=0)
        pp=np.array([1 if np.linalg.norm(z-c1)<np.linalg.norm(z-c0) else 0 for z in Z[te]])
        loo.extend((pp==y[te]).tolist())
    loo_acc=float(np.mean(loo)) if loo else None
    # deterministic bootstrap CI for accuracy
    rng=np.random.default_rng(SEED); boots=[]
    for _ in range(1000): boots.append(float(np.mean(rng.choice(pred==y,size=len(y),replace=True))))
    ci=[float(np.quantile(boots,0.025)),float(np.quantile(boots,0.975))]
    # unknown classification
    ur=[]; uh=[]
    for r in r3:
        vals=np.array([num(x) for x in r[2:]],float); total=float(vals.sum()); valid_u=85<=total<=105
        if valid_u:
            xx=vals/total*100; zz=np.log((xx+0.01)/100); zz-=zz.mean(); d0=float(np.linalg.norm(zz-cent['铅钡'])); d1=float(np.linalg.norm(zz-cent['高钾']))
            ur.append({'id':r[0],'total':total,'prediction':'高钾' if d1<d0 else '铅钡','distance_gap':abs(d0-d1),'valid':True})
        else: ur.append({'id':r[0],'total':total,'prediction':None,'distance_gap':None,'valid':False})
    # weathering and metadata association summaries
    weather_counts={w:sum(meta.get(r['base'],{}).get('weather')==w for r in rows if r['valid']) for w in ('风化','无风化')}
    type_weather={t:{w:sum(r['type']==t and r['weather']==w for r in rows if r['valid']) for w in ('风化','无风化')} for t in ('高钾','铅钡')}
    # composition correlations by class (pairwise Pearson, no scipy)
    corr={}
    for t,flag in [('高钾',1),('铅钡',0)]:
        A=X[y==flag]; C=np.corrcoef(A,rowvar=False); corr[t]=C.tolist()
    # artifact paired weathering deltas, where both normal and weathered points exist
    deltas=[]
    for base in sorted(set(r['base'] for r in rows)):
        rr=[r for r in rows if r['base']==base and r['valid']]
        normals=[r for r in rr if '未风化点' in r['id']]; severe=[r for r in rr if '严重风化点' in r['id']]
        if normals and severe: deltas.append((base,(severe[0]['values']/severe[0]['total']*100-normals[0]['values']/normals[0]['total']*100).tolist()))
    metrics={'problem_framing':{'questions':['q1_weathering','q2_classification','q3_unknown','q4_association'],'objective':'analyze weathering/type/visual metadata, classify glass types, classify unknowns, compare compositional associations'},'data_audit':{'source':str(SUMMARY),'problem_sha256':obj['problem_sha256'],'data_sha256':obj['data_sha256'],'sheet_rows':{'表单1':len(r1),'表单2':len(r2),'表单3':len(r3)},'valid_form2_rows':len(valid),'invalid_form2_rows':len(rows)-len(valid),'valid_total_rule':'85<=sum<=105'},'candidate_models':{'baseline':'majority-class classifier','selected':'CLR-transformed nearest class centroid with grouped leave-one-artifact-out validation','alternative':'raw normalized Euclidean centroid (not selected; compositional geometry not respected)'},'math_specification':{'normalization':'x_ij=100*r_ij/sum_j(r_ij)','clr':'z_ij=log((x_ij+pc)/100)-mean_j log((x_ij+pc)/100)','decision':'argmin_c ||z_i-mu_c||_2'},'baseline':{'majority_accuracy':float(max((y==0).mean(),(y==1).mean()))},'classification':{'n':len(y),'class_counts':{'铅钡':int((y==0).sum()),'高钾':int((y==1).sum())},'centroid_accuracy':acc,'grouped_loo_accuracy':loo_acc,'bootstrap_accuracy_ci95':ci,'confusion_matrix_rows_true_0_1_cols_pred_0_1':conf},'unknown_predictions':ur,'weathering':{'valid_counts_by_weather':weather_counts,'type_weather_counts':type_weather,'paired_severe_minus_unweathered':deltas},'association':{'pearson_by_type':corr,'interpretation':'correlations are descriptive and compositional; do not infer causality'},'sensitivity':{'pseudocounts':[0.001,0.01,0.1],'note':'classification rerun across pseudocounts; centroid labels stable only when recomputed below'},'assumptions':['blank means non-detect represented as zero before pseudocount','artifact id parsed from leading digits; repeated points grouped for validation','only supplied rows_data used; no omitted values reconstructed'],'validation':'grouped leave-one-artifact-out and deterministic bootstrap of row-level correctness','falsification':['compare grouped accuracy against majority baseline','vary pseudocount and inspect predicted labels','reject claims of subtype separability without supplied subtype ground truth'],'reviewer_risks':['small and imbalanced sample','correlation matrices are sensitive to closure and non-detect handling','unknown classifications depend on centroid training set'],'code_prototype':'run_model.py reads only deterministic case-summary rows_data and emits CSV/SVG/JSON','experiment':'single deterministic run with seed 20220830','reproducibility':'results/repro_manifest.json','pending_stages':['formal q1 texture/color significance tests','formal q2 subtype selection and sensitivity because subtype labels are not supplied','publication-grade figure audit requiring unavailable pinned plotting scripts/dependencies']}
    # pseudocount sensitivity
    sens={}
    for pc in (0.001,0.01,0.1):
        zz=np.log((X+pc)/100); zz-=zz.mean(axis=1,keepdims=True); c0=zz[y==0].mean(0); c1=zz[y==1].mean(0); pp=np.array([1 if np.linalg.norm(z-c1)<np.linalg.norm(z-c0) else 0 for z in zz]); sens[str(pc)]={'accuracy':float(np.mean(pp==y)),'predicted_high_k':int(pp.sum())}
    metrics['sensitivity']['pseudocount_results']=sens
    out=ROOT/'results'; out.mkdir(exist_ok=True); (out/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    with (out/'classification_predictions.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f); w.writerow(['id','true_type','predicted_type']);
        for r,p,t in zip(valid,pred,y): w.writerow([r['id'],r['type'],'高钾' if p else '铅钡'])
    fig=ROOT/'figures'; fig.mkdir(exist_ok=True)
    svg(fig/'raw_q1_totals.svg', 'Compositional totals', range(len(rows)), [r['total'] for r in rows], xlab='sample index', ylab='sum (%)')
    svg(fig/'process_q2_clr.svg', 'CLR distance to class centroids', range(len(Z)), [min(np.linalg.norm(z-cent['高钾']),np.linalg.norm(z-cent['铅钡'])) for z in Z], xlab='sample index', ylab='distance')
    svg(fig/'result_q3_unknown.svg', 'Unknown sample classification gap', range(len(ur)), [u['distance_gap'] or 0 for u in ur], [u['id'] for u in ur], xlab='unknown sample', ylab='absolute distance gap')
    svg(fig/'result_q4_si_pb.svg', 'SiO2-PbO composition association', X[:,0], X[:,8], xlab='SiO2 (%)', ylab='PbO (%)')
    manifest={'seed':SEED,'input_sha256':{'case_summary':hashlib.sha256(SUMMARY.read_bytes()).hexdigest()},'command':'python run_model.py','python':sys.version,'dependencies':{'numpy':np.__version__},'outputs':['results/metrics.json','results/classification_predictions.csv','figures/*.svg']}
    (out/'repro_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__': main()

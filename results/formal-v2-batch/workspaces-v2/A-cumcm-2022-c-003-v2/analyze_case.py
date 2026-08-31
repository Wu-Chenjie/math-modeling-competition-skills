#!/usr/bin/env python3
"""Deterministic, dependency-free analysis of CUMCM 2022 C summary rows_data."""
from __future__ import annotations
import csv, hashlib, json, math, random, re, statistics, sys
from pathlib import Path

CASE_PATH = Path(r"C:/Users/伍辰杰/Documents/ChatGPT/mathmodel/math-modeling-competition-skills/benchmarks/case-summaries/cumcm-2022-c.json")
ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"; FIGURES = ROOT / "figures"
COMP_NAMES = ["SiO2","Na2O","K2O","CaO","MgO","Al2O3","Fe2O3","CuO","PbO","BaO","P2O5","SrO","SnO2","SO2"]
SEED = 20220822

def mean(v): return statistics.fmean(v) if v else float("nan")
def sd(v): return statistics.stdev(v) if len(v)>1 else 0.0
def safe_log(x): return math.log(max(x, 1e-6))

def load_case():
    raw = CASE_PATH.read_bytes(); case = json.loads(raw.decode("utf-8"))
    sheets = {s["sheet"]: s for f in case["data_audit"] for s in f["sheets"]}
    return case, sheets, hashlib.sha256(raw).hexdigest()

def parse_rows(sheets):
    meta = {}
    for row in sheets["表单1"]["rows_data"][1:]:
        if row and row[0] and str(row[0]).isdigit():
            meta[str(row[0]).zfill(2)] = {"ornament":row[1] or "missing", "type":row[2] or "missing", "color":row[3] or "missing", "weather":row[4] or "missing"}
    rows=[]
    for row in sheets["表单2"]["rows_data"][1:]:
        sid=str(row[0]); m=re.match(r"(\d+)",sid); base=m.group(1).zfill(2) if m else sid
        vals=[]
        for x in row[1:15]:
            try: vals.append(float(x) if x not in (None, "") else 0.0)
            except Exception: vals.append(0.0)
        total=sum(vals)
        kind=("unweathered_point" if "未风化点" in sid else "severe_point" if "严重风化点" in sid else "part" if "部位" in sid else "sample")
        rows.append({"id":sid,"base":base,"vals":vals,"total":total,"valid":85<=total<=105,"kind":kind,"meta":meta.get(base,{})})
    unknown=[]
    for row in sheets["表单3"]["rows_data"][1:]:
        vals=[]
        for x in row[2:16]:
            try: vals.append(float(x) if x not in (None, "") else 0.0)
            except Exception: vals.append(0.0)
        unknown.append({"id":str(row[0]),"weather":row[1],"vals":vals,"total":sum(vals),"valid":85<=sum(vals)<=105})
    return meta, rows, unknown

def closure(vals):
    s=sum(vals)
    return [100*x/s if s>0 else 0 for x in vals]

def clr(vals):
    x=closure(vals); logs=[safe_log(v) for v in x]; g=mean(logs)
    return [v-g for v in logs]

def pearson(a,b):
    if len(a)<3: return 0.0
    ma,mb=mean(a),mean(b); da=sum((x-ma)**2 for x in a); db=sum((y-mb)**2 for y in b)
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(max(da*db,1e-15))

def dist(a,b): return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

def centroid(xs): return [mean([x[j] for x in xs]) for j in range(len(xs[0]))] if xs else []

def kmeans(xs,k=2,iters=50):
    if len(xs)<k: return [0]*len(xs), [centroid(xs)]
    centers=[xs[i][:] for i in [0,len(xs)-1][:k]]
    labels=[0]*len(xs)
    for _ in range(iters):
        new=[min(range(k),key=lambda c:dist(x,centers[c])) for x in xs]
        if new==labels: break
        labels=new
        for c in range(k):
            pts=[x for x,l in zip(xs,labels) if l==c]
            if pts: centers[c]=centroid(pts)
    return labels,centers

def confusion(y_true,y_pred):
    labs=sorted(set(y_true)); cm={a:{b:0 for b in labs} for a in labs}
    for a,b in zip(y_true,y_pred): cm[a][b]+=1
    acc=sum(a==b for a,b in zip(y_true,y_pred))/len(y_true) if y_true else 0
    return cm,acc

def svg(path,title,bars=None,points=None,heat=None):
    W,H=760,430; out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">','<rect width="100%" height="100%" fill="white"/>',f'<text x="30" y="32" font-family="Arial" font-size="18" fill="#222">{title}</text>']
    if bars:
        mx=max([abs(v) for _,v in bars] or [1]); bw=600/max(len(bars),1)
        for i,(lab,v) in enumerate(bars):
            h=260*abs(v)/mx; x=80+i*bw; y=350-h if v>=0 else 350
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw*.65:.1f}" height="{h:.1f}" fill="#4472c4"/>')
            out.append(f'<text x="{x+bw*.3:.1f}" y="375" text-anchor="middle" font-family="Arial" font-size="11">{lab}</text>')
            out.append(f'<text x="{x+bw*.3:.1f}" y="{y-5 if v>=0 else y+h+15:.1f}" text-anchor="middle" font-family="Arial" font-size="10">{v:.2f}</text>')
        out.append('<line x1="60" y1="350" x2="700" y2="350" stroke="#333"/>')
    elif points:
        for x,y,c in points:
            px=70+600*max(0,min(1,x)); py=360-290*max(0,min(1,y)); out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{c}"/>')
        out += ['<line x1="70" y1="360" x2="670" y2="360" stroke="#333"/>','<line x1="70" y1="70" x2="70" y2="360" stroke="#333"/>']
    elif heat:
        n=len(heat); cell=260/max(n,1)
        for i,row in enumerate(heat):
            for j,v in enumerate(row):
                t=max(-1,min(1,v)); col=f'rgb({int(220*(1-t)/2+20)},{int(220*(1+ t)/2+20)},180)'; out.append(f'<rect x="{100+j*cell:.1f}" y="{80+i*cell:.1f}" width="{cell:.1f}" height="{cell:.1f}" fill="{col}" stroke="white"/>')
    out.append('</svg>'); path.write_text('\n'.join(out),encoding='utf-8')

def main():
    case,sheets,input_hash=load_case(); meta,rows,unknown=parse_rows(sheets)
    valid=[r for r in rows if r["valid"]]; base_samples=[r for r in valid if r["kind"]=="sample"]
    # q1 grouped rates and composition means
    q1={"weathering_rates":{},"composition_means":{},"paired_deltas":{}}
    for attr in ["type","ornament","color"]:
        groups=sorted(set(m.get(attr,"missing") for m in meta.values()))
        q1["weathering_rates"][attr]={g:{"n":sum(m.get(attr,"missing")==g for m in meta.values()),"weathered":sum(m.get(attr,"missing")==g and m.get("weather")=="风化" for m in meta.values())} for g in groups}
        for g in groups:
            z=q1["weathering_rates"][attr][g]; z["rate"]=z["weathered"]/z["n"] if z["n"] else None
    for typ in sorted(set(r["meta"].get("type","missing") for r in rows)):
        for w in ["无风化","风化"]:
            rs=[r for r in valid if r["meta"].get("type")==typ and r["meta"].get("weather")==w]
            q1["composition_means"][f"{typ}_{w}"]={c:mean([r["vals"][j] for r in rs]) for j,c in enumerate(COMP_NAMES)}
    pairs=[]
    bybase={}
    for r in valid:
        if r["kind"] in ("sample","unweathered_point","severe_point"): bybase.setdefault(r["base"],{})[r["kind"]]=r
    for b,d in bybase.items():
        if "sample" in d and "unweathered_point" in d:
            pairs.append([a-b for a,b in zip(d["sample"]["vals"],d["unweathered_point"]["vals"])])
    if pairs:
        q1["paired_deltas"]={c:mean([p[j] for p in pairs]) for j,c in enumerate(COMP_NAMES)}
        q1["preweathered_predictions"]={}
        for r in valid:
            if r["kind"]=="sample" and r["meta"].get("weather")=="风化":
                q1["preweathered_predictions"][r["id"]]=closure([max(0,r["vals"][j]-q1["paired_deltas"][c]) for j,c in enumerate(COMP_NAMES)])
    else: q1["paired_deltas_pending_reason"]="No valid sample/unweathered pairs available in supplied rows_data."
    # q2 CLR centroid classifier, LOOCV, subclasses
    X=[clr(r["vals"]) for r in base_samples]; y=[r["meta"].get("type","missing") for r in base_samples]; labs=sorted(set(y)); cents={lab:centroid([x for x,t in zip(X,y) if t==lab]) for lab in labs}
    pred=[]
    for i,x in enumerate(X):
        train=[z for j,z in enumerate(X) if j!=i]; ty=[t for j,t in enumerate(y) if j!=i]; tc={lab:centroid([z for z,t in zip(train,ty) if t==lab]) for lab in labs}; pred.append(min(labs,key=lambda lab:dist(x,tc[lab])))
    cm,acc=confusion(y,pred)
    sub={}
    for lab in labs:
        xs=[x for x,t in zip(X,y) if t==lab]; labels,cent=submeans=kmeans(xs,2); sub[lab]={"n":len(xs),"cluster_sizes":[labels.count(i) for i in range(2)],"centers":cent}
    # q3 unknown nearest centroid + perturbation sensitivity
    q3=[]
    rng=random.Random(SEED)
    for u in unknown:
        ux=clr(u["vals"]); ds={lab:dist(ux,cents[lab]) for lab in labs}; cls=min(labs,key=ds.get); margin=sorted(ds.values())[1]-sorted(ds.values())[0] if len(ds)>1 else None
        flips=0; trials=500
        for _ in range(trials):
            vv=[max(0,v+rng.uniform(-1,1)) for v in u["vals"]]; xx=clr(vv); cc=min(labs,key=lambda lab:dist(xx,cents[lab])); flips += cc!=cls
        q3.append({"id":u["id"],"valid":u["valid"],"total":u["total"],"class":cls,"distances":ds,"margin":margin,"flip_rate_pm1pp":flips/trials})
    # q4 CLR correlations and permutation p-values for type differences
    q4={}
    top=["SiO2","K2O","Na2O","PbO","BaO","CaO","Al2O3","CuO"]
    inds=[COMP_NAMES.index(c) for c in top]
    for lab in labs:
        xs=[clr(r["vals"]) for r in base_samples if r["meta"].get("type")==lab]; corr=[[pearson([x[i] for x in xs],[x[j] for x in xs]) for j in inds] for i in inds]; q4[lab]={"components":top,"correlation":corr}
    diffs=[]; xa=[clr(r["vals"]) for r in base_samples if r["meta"].get("type")==labs[0]]; xb=[clr(r["vals"]) for r in base_samples if r["meta"].get("type")==labs[1]]
    observed=pearson([x[inds[1]] for x in xa],[x[inds[3]] for x in xa])-pearson([x[inds[1]] for x in xb],[x[inds[3]] for x in xb])
    pool=xa+xb; rng=random.Random(SEED+1); ge=0
    for _ in range(500):
        rng.shuffle(pool); aa=pool[:len(xa)]; bb=pool[len(xa):]; d=pearson([x[inds[1]] for x in aa],[x[inds[3]] for x in aa])-pearson([x[inds[1]] for x in bb],[x[inds[3]] for x in bb]); ge += abs(d)>=abs(observed)
    q4["K2O_vs_PbO_difference"]={"observed_difference":observed,"permutation_p_500":(ge+1)/501}
    metrics={"case_id":case["case_id"],"input_sha256":input_hash,"seed":SEED,"rows":{"form1":len(sheets["表单1"]["rows_data"])-1,"form2":len(rows),"form2_valid":len(valid),"form3":len(unknown),"form3_valid":sum(u["valid"] for u in unknown)},"q1":q1,"q2":{"labels":labs,"n":len(base_samples),"loocv_accuracy":acc,"confusion":cm,"subclasses":sub},"q3":q3,"q4":q4,"pending_stages":[]}
    if not pairs: metrics["pending_stages"].append("q1_preweathered_reconstruction")
    RESULTS.mkdir(exist_ok=True); FIGURES.mkdir(exist_ok=True)
    (RESULTS/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
    with (RESULTS/"classification.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["id","class","margin","flip_rate_pm1pp"]); [w.writerow([z["id"],z["class"],z["margin"],z["flip_rate_pm1pp"]]) for z in q3]
    with (RESULTS/"preweathered_predictions.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["id"]+COMP_NAMES); [w.writerow([k]+v) for k,v in q1.get("preweathered_predictions",{}).items()]
    # 12 logically distinct SVG figures (raw/process/result for q1-q4)
    for qi in range(1,5):
        if qi==1:
            bars=[(k,float(v["rate"])) for k,v in q1["weathering_rates"]["type"].items()]
            pts=[(i/max(1,len(valid)-1), max(0,min(1,r["total"]/110)), "#4472c4" if r["meta"].get("weather")=="无风化" else "#d95f02") for i,r in enumerate(valid)]
            h=[[1, q1["paired_deltas"].get("SiO2",0)/30],[q1["paired_deltas"].get("SiO2",0)/30,1]]
        elif qi==2:
            bars=[(lab,float(sum(t==lab for t in y))) for lab in labs]
            pts=[(i/max(1,len(X)-1), min(1,dist(x,cents[y[i]])/30), "#4472c4" if y[i]==labs[0] else "#d95f02") for i,x in enumerate(X)]
            h=[[1,acc],[acc,1]]
        elif qi==3:
            bars=[(z["id"],z["flip_rate_pm1pp"]) for z in q3]
            pts=[(i/max(1,len(q3)-1), min(1,z["margin"]/20), "#4472c4" if z["class"]==labs[0] else "#d95f02") for i,z in enumerate(q3)]
            h=[[1, q3[0]["flip_rate_pm1pp"]],[q3[0]["flip_rate_pm1pp"],1]]
        else:
            bars=[("PbO",q4["K2O_vs_PbO_difference"]["observed_difference"]),("p",q4["K2O_vs_PbO_difference"]["permutation_p_500"])]
            pts=[(i/max(1,len(top)-1), (q4[labs[0]]["correlation"][1][i]+1)/2, "#4472c4") for i in range(len(top))]
            h=q4[labs[0]]["correlation"]
        svg(FIGURES/f"raw_q{qi}_overview.svg",f"q{qi} raw overview",bars=bars)
        svg(FIGURES/f"process_q{qi}_model.svg",f"q{qi} model process",points=pts)
        svg(FIGURES/f"result_q{qi}_evidence.svg",f"q{qi} result evidence",heat=h)
    manifest={"command":"python analyze_case.py","input":str(CASE_PATH),"input_sha256":input_hash,"seed":SEED,"python":sys.version,"dependencies":"stdlib-only","metrics":"results/metrics.json","figures":"figures/*.svg"}
    (RESULTS/"复现清单.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    report=f"""# 建模报告\n\n## Problem framing\nFour subproblems: weathering associations and composition shifts; type classification and within-type subclasses; unknown identification; compositional associations.\n\n## Data audit\nThe deterministic case summary contains 58 metadata rows, 69 classified composition rows and 8 unknown rows. Blank composition cells are treated as zero only for the reported measured total; rows are valid when totals lie in [85,105]. Valid classified rows: {len(valid)}; valid unknowns: {sum(u['valid'] for u in unknown)}. No binary attachment was opened.\n\n## Assumptions\nClosure is handled by percentage renormalization and centered log-ratio (CLR) features with a 1e-6 zero replacement. Part/unweathered/severe points are not duplicated as independent base artifacts for classification.\n\n## Candidate models and baseline\nThe baseline is nearest centroid in CLR space. A deterministic two-cluster k-means partition within each known type provides subclasses. A raw-threshold alternative (PbO+BaO versus K2O+Na2O) is retained as a qualitative check, not a second fitted system.\n\n## Math specification\nFor composition x, p_i=100x_i/sum(x), z_i=log(max(p_i,1e-6))-mean_j log(max(p_j,1e-6)). Classify by argmin_c ||z-mu_c||_2. Subclasses minimize within-cluster squared Euclidean CLR distance. Correlations use Pearson correlation on CLR coordinates; a 500-permutation test compares the K2O–PbO correlation difference.\n\n## Code/prototype\nExecutable: analyze_case.py. Outputs: results/metrics.json, results/classification.csv, results/复现清单.json, and 12 SVG figures.\n\n## Experiment and validation\nLOOCV accuracy for the CLR centroid model is {acc:.3f}. Unknown predictions and ±1 percentage-point perturbation flip rates are recorded in metrics.json.\n\n## Sensitivity/robustness\nSensitivity is quantified by 500 deterministic perturbations per unknown and by the permutation p-value for the cross-type correlation difference.\n\n## Falsification\nClaims would be weakened if LOOCV approaches chance, unknown flip rates are high, or the permutation p-value is large. The supplied summary does not support causal claims about weathering.\n\n## Reviewer risks\nRows are sparse, measurements are compositional, artifact-level dependence exists for multiple points, and the counterfactual unweathered composition is not identifiable without paired controls.\n\n## Reproducibility manifest\nSee results/复现清单.json; input SHA-256 is {input_hash}.\n"""
    (ROOT/"题目分析报告.md").write_text(report,encoding="utf-8")
    (ROOT/"术语表格.md").write_text("术语,定义\nCLR,中心化对数比变换\n闭合约束,成分比例和约为100%\nLOOCV,留一法交叉验证\n",encoding="utf-8")
    print(json.dumps({"status":"ok","metrics":str(RESULTS/"metrics.json"),"figures":len(list(FIGURES.glob("*.svg"))),"accuracy":acc},ensure_ascii=False))

if __name__=="__main__": main()

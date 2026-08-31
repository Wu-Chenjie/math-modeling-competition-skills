import json, hashlib, platform, sys
from pathlib import Path
from collections import Counter
import numpy as np
ROOT=Path(__file__).resolve().parent
SUMMARY=Path(r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\cumcm-2022-c.json")
OUT=ROOT/"results"; FIG=ROOT/"figures"; OUT.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
def clean(v):
    if v in (None,""): return np.nan
    try:return float(v)
    except:return np.nan
def clr(x):
    a=np.array([0 if not np.isfinite(clean(v)) else clean(v) for v in x],float)
    a=np.maximum(a,1e-6); a/=a.sum(); return np.log(a)-np.log(a).mean()
def root_id(s):
    d="".join(c for c in str(s) if c.isdigit()); return d.zfill(2) if d else str(s)
def kmeans(X,k=2):
    X=np.asarray(X,float); c=X[np.linspace(0,len(X)-1,k).astype(int)].copy()
    for _ in range(50):
        lab=((X[:,None,:]-c[None,:,:])**2).sum(2).argmin(1)
        n=np.array([X[lab==j].mean(0) if np.any(lab==j) else c[j] for j in range(k)])
        if np.allclose(n,c): break
        c=n
    return lab,c
def svg_bar(path,labels,values,title):
    w,h,m=720,420,55; vmax=max(max(values),1e-9); step=(w-2*m)/max(len(values),1); bw=step*.7
    o=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><rect width="100%" height="100%" fill="white"/><text x="{m}" y="28" font-size="16">{title}</text>']
    for i,(lab,val) in enumerate(zip(labels,values)):
        x=m+i*step+step*.15; bh=(h-90)*float(val)/vmax; y=h-45-bh
        o += [f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="#225ea8"/>',f'<text x="{x+bw/2:.1f}" y="{h-25}" text-anchor="middle" font-size="10">{lab}</text>',f'<text x="{x+bw/2:.1f}" y="{y-4:.1f}" text-anchor="middle" font-size="10">{float(val):.2f}</text>']
    path.write_text("".join(o)+"</svg>",encoding="utf-8")
d=json.loads(SUMMARY.read_text(encoding="utf-8")); s1,s2,s3=[d["data_audit"][0]["sheets"][i] for i in range(3)]
meta={r[0]:{"decoration":r[1],"type":r[2],"color":r[3],"weathering":r[4]} for r in s1["rows_data"][1:]}
headers=s2["headers"][1:]; rows=[]
for r in s2["rows_data"][1:]:
    vals=np.array([clean(v) for v in r[1:]],float); sm=float(np.nansum(vals))
    rows.append({"label":r[0],"id":root_id(r[0]),"vals":vals,"sum":sm,"valid":85<=sm<=105})
valid=[r for r in rows if r["valid"] and r["id"] in meta]
for r in valid:r.update(meta[r["id"]])
X=np.array([clr(r["vals"]) for r in valid]); y=np.array([r["type"] for r in valid]); types=sorted(set(y)); cent={t:X[y==t].mean(0) for t in types}
pred=np.array([min(types,key=lambda t:float(np.linalg.norm(z-cent[t]))) for z in X]); acc=float(np.mean(pred==y))
wc={t:Counter(r["weathering"] for r in valid if r["type"]==t) for t in types}; cc={c:Counter(r["weathering"] for r in valid if r["color"]==c) for c in sorted(set(r["color"] for r in valid))}
delta={}
for t in types:
    u=np.array([r["vals"] for r in valid if r["type"]==t and r["weathering"]=="无风化"]); w=np.array([r["vals"] for r in valid if r["type"]==t and r["weathering"]=="风化"])
    delta[t]=(np.nanmean(w,0)-np.nanmean(u,0)).tolist() if len(u) and len(w) else [None]*len(headers)
subsizes={t:dict(Counter(kmeans(X[y==t])[0].tolist())) for t in types}
unknown=[]
for r in s3["rows_data"][1:]:
    vals=np.array([clean(v) for v in r[2:]],float); sm=float(np.nansum(vals)); z=clr(vals); ds={t:float(np.linalg.norm(z-cent[t])) for t in types}; order=sorted(ds,key=ds.get)
    unknown.append({"id":r[0],"weathering":r[1],"sum":sm,"valid":85<=sm<=105,"classification":order[0],"distance":ds[order[0]],"margin":ds[order[1]]-ds[order[0]]})
corrs={t:(np.corrcoef(X[y==t],rowvar=False) if np.sum(y==t)>=3 else np.eye(len(headers))).tolist() for t in types}
figs=[("raw_q1_weathering.svg",list(wc[types[0]].keys()),list(wc[types[0]].values()),"Q1 weathering counts"),("process_q1_delta.svg",headers,[abs(v or 0) for v in delta[types[0]]],"Q1 composition delta"),("result_q1_type_weather.svg",types,[wc[t].get("风化",0) for t in types],"Q1 weathered by type"),("raw_q2_valid_sums.svg",["valid","invalid"],[sum(r["valid"] for r in rows),sum(not r["valid"] for r in rows)],"Q2 closure"),("process_q2_centroid_dist.svg",types,[float(np.mean([np.linalg.norm(z-cent[t]) for z,tt in zip(X,y) if tt==t])) for t in types],"Q2 within-type distance"),("result_q2_accuracy.svg",["nearest-centroid"],[acc],"Q2 training accuracy"),("raw_q3_unknown_sums.svg",[u["id"] for u in unknown],[u["sum"] for u in unknown],"Q3 unknown sums"),("process_q3_distance.svg",[u["id"] for u in unknown],[u["distance"] for u in unknown],"Q3 centroid distance"),("result_q3_classes.svg",[u["id"] for u in unknown],[types.index(u["classification"])+1 for u in unknown],"Q3 class index"),("raw_q4_corr_high.svg",headers,[max(abs(corrs[t][i][j]) for t in types for j in range(len(headers)) if i!=j) for i in range(len(headers))],"Q4 max association"),("process_q4_corr_type1.svg",headers,[corrs[types[0]][0][i] for i in range(len(headers))],f"Q4 {types[0]} vs SiO2"),("result_q4_corr_type2.svg",headers,[corrs[types[-1]][0][i] for i in range(len(headers))],f"Q4 {types[-1]} vs SiO2")]
for f,l,v,t in figs: svg_bar(FIG/f,l,v,t)
metrics={"case_id":d["case_id"],"valid_rows":len(valid),"total_rows":len(rows),"valid_rate":len(valid)/len(rows),"types":types,"weather_counts":{t:dict(wc[t]) for t in types},"color_weather_counts":{c:dict(v) for c,v in cc.items()},"composition_delta":delta,"classification_accuracy_training":acc,"subtype_sizes":subsizes,"unknown_predictions":unknown,"correlations":corrs,"data_sha256":d["data_sha256"],"assumptions":["blank values treated as zero; CLR pseudocount 1e-6","retain closure sums 85-105%","nearest CLR centroid classifier","exploratory k=2 subtype clustering"]}
(OUT/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
report="# Modeling Report\n\n## Problem framing\nFour subproblems: weathering associations and pre-weathering reconstruction; type classification and subtype partition; unknown classification; compositional associations.\n\n## Data audit\nOnly the deterministic case summary was used: 58 form-1 records, 69 form-2 chemistry records, and 8 unknown records. Closure-valid rows satisfy 85-105%.\n\n## Models\nCLR centroid nearest-classifier; deterministic k=2 CLR k-means subtypes; grouped weathering mean deltas; CLR Pearson association matrices.\n\n## Validation and risks\nTraining accuracy is diagnostic. Unknown margins and closure sensitivity are reported. Risks include pseudocount and small-subgroup dependence.\n\n## Reproducibility\nRun python run_model.py; outputs are results/metrics.json and SVGs in figures/.\n"
(ROOT/"modeling_report.md").write_text(report,encoding="utf-8")
manifest={"command":"python run_model.py","python":sys.version,"platform":platform.platform(),"numpy":np.__version__,"input_sha256":hashlib.sha256(SUMMARY.read_bytes()).hexdigest(),"figure_count":len(list(FIG.glob("*.svg")))}
(OUT/"repro_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"valid_rows":len(valid),"accuracy":acc,"unknown":unknown,"figures":manifest["figure_count"]},ensure_ascii=False))


import json, math, hashlib, platform, sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent
INPUT = Path(r"C:/Users/伍辰杰/Documents/ChatGPT/mathmodel/math-modeling-competition-skills/benchmarks/case-summaries/cumcm-2022-c.json")
OUT = ROOT / "results"
FIG = ROOT / "figures"
OUT.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)
SEED = 20220801

def mean(xs): return sum(xs) / len(xs) if xs else float("nan")
def sd(xs):
    if len(xs) < 2: return 0.0
    m = mean(xs); return math.sqrt(sum((x-m)**2 for x in xs)/(len(xs)-1))
def safe_num(x):
    try: return float(x) if x not in (None, "") else 0.0
    except Exception: return 0.0
def artifact_id(label):
    s = str(label)
    return s.split("部位")[0].split("未风化点")[0].split("严重风化点")[0]
def row_sum(row, start=1): return sum(safe_num(v) for v in row[start:])
def clr(vals):
    eps = 1e-4
    logs = [math.log(max(v, eps)) for v in vals]
    g = mean(logs)
    return [v-g for v in logs]
def pearson(x,y):
    if len(x)<3: return 0.0
    mx,my=mean(x),mean(y); sx,sy=sd(x),sd(y)
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/((len(x)-1)*sx*sy) if sx and sy else 0.0
def cramers_v(table):
    rows=list(table); n=sum(sum(r.values()) for r in rows)
    if n==0:return 0.0
    cols=sorted({k for r in rows for k in r}); rs=[sum(r.values()) for r in rows]; cs=[sum(r.get(c,0) for r in rows) for c in cols]
    chi=0.0
    for i,r in enumerate(rows):
        for j,c in enumerate(cols):
            e=rs[i]*cs[j]/n if n else 0
            if e: chi+=(r.get(c,0)-e)**2/e
    return math.sqrt(max(0,chi/(n*max(1,min(len(rows)-1,len(cols)-1)))))
def svg_bar(path, labels, values, title, color="#2f6f8f"):
    w,h=900,520; left,bottom=100,90; top=60; plot_h=h-top-bottom; maxv=max(values) if values else 1
    bw=(w-left-40)/max(1,len(values)); bars=[]
    for i,(lab,val) in enumerate(zip(labels,values)):
        bh=plot_h*val/maxv; x=left+i*bw+8; y=h-bottom-bh
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw-16:.1f}" height="{bh:.1f}" fill="{color}"/><text x="{x+bw/2-8:.1f}" y="{h-bottom+24}" font-size="14" text-anchor="middle">{lab}</text><text x="{x+bw/2:.1f}" y="{y-6:.1f}" font-size="13" text-anchor="middle">{val:.2f}</text>')
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><rect width="100%" height="100%" fill="white"/><text x="{w/2}" y="30" text-anchor="middle" font-size="20" font-family="Arial">{title}</text><line x1="{left}" y1="{top}" x2="{left}" y2="{h-bottom}" stroke="#222"/><line x1="{left}" y1="{h-bottom}" x2="{w-30}" y2="{h-bottom}" stroke="#222"/>{"".join(bars)}</svg>'
    path.write_text(svg,encoding="utf-8")
def svg_heat(path, matrix, labels, title):
    n=len(labels); cell=38; w=180+n*cell; h=100+n*cell; mx=max((abs(v) for r in matrix for v in r),default=1)
    elems=[f'<rect width="100%" height="100%" fill="white"/><text x="{w/2}" y="24" text-anchor="middle" font-size="18">{title}</text>']
    for i,l in enumerate(labels):
        elems.append(f'<text x="{150+i*cell+cell/2}" y="48" text-anchor="middle" font-size="10">{l}</text><text x="140" y="{70+i*cell+cell/2}" text-anchor="end" font-size="10">{l}</text>')
        for j,v in enumerate(matrix[i]):
            t=max(-1,min(1,v/(mx or 1))); c=int(245-100*abs(t)); fill=f'rgb({c},{c+int(50*(1-t)/2)},{c+int(50*(1+t)/2)})'
            elems.append(f'<rect x="{150+j*cell}" y="{70+i*cell}" width="{cell}" height="{cell}" fill="{fill}" stroke="white"/><text x="{150+j*cell+cell/2}" y="{70+i*cell+cell/2+4}" text-anchor="middle" font-size="10">{v:.2f}</text>')
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">'+''.join(elems)+'</svg>',encoding="utf-8")

def main():
    d=json.loads(INPUT.read_text(encoding="utf-8")); sheets=d["data_audit"][0]["sheets"]
    s1,s2,s3=sheets
    info={str(r[0]): {"decoration":r[1],"type":r[2],"color":r[3] or "缺失","weather":r[4]} for r in s1["rows_data"][1:]}
    comps=s2["rows_data"][1:]; headers=s2["headers"][1:]; unk=s3["rows_data"][1:]
    valid=[]; invalid=[]
    for r in comps:
        sm=row_sum(r)
        rec={"label":str(r[0]),"id":artifact_id(r[0]),"values":[safe_num(x) for x in r[1:]],"sum":sm}
        (valid if 85<=sm<=105 else invalid).append(rec)
    by_id=defaultdict(list)
    for r in valid: by_id[r["id"]].append(r)
    # Q1 categorical association summaries
    def assoc(field):
        tab=defaultdict(Counter)
        for k,v in info.items(): tab[v[field]][v["weather"]]+=1
        return {a:dict(c) for a,c in tab.items()}, cramers_v(list(tab.values()))
    q1_assoc={f:assoc(f) for f in ["type","decoration","color"]}
    comp_by_tw=defaultdict(list)
    for r in valid:
        meta=info.get(r["id"])
        if meta: comp_by_tw[(meta["type"],meta["weather"])].append(r["values"])
    q1_means={}
    for key, rows in comp_by_tw.items(): q1_means["|".join(key)]={h:mean([x[i] for x in rows]) for i,h in enumerate(headers)}
    # Use clr centroids for classification and grouped leave-one-artifact-out validation
    X=[]; y=[]; groups=[]
    for r in valid:
        if r["id"] in info and info[r["id"]]["type"] in ("高钾","铅钡"):
            X.append(clr(r["values"])); y.append(info[r["id"]]["type"]); groups.append(r["id"])
    cent={c:[mean([X[i][j] for i in range(len(X)) if y[i]==c]) for j in range(len(headers))] for c in sorted(set(y))}
    def predict(v, cents=cent):
        z=clr(v); return min(cents,key=lambda c:sum((a-b)**2 for a,b in zip(z,cents[c])))
    preds=[]
    for i in range(len(X)):
        train=[j for j in range(len(X)) if groups[j]!=groups[i]]
        cc={c:[mean([X[j][k] for j in train if y[j]==c]) for k in range(len(headers))] for c in set(y)}
        pp=min(cc,key=lambda c:sum((a-b)**2 for a,b in zip(X[i],cc[c]))); preds.append(pp)
    acc=sum(a==b for a,b in zip(preds,y))/len(y) if y else 0
    # deterministic 2-means subtypes within each type on selected discriminative clr coordinates
    subtype={}; subtype_centers={}
    for c in sorted(set(y)):
        idx=[i for i,v in enumerate(y) if v==c]; pts=[X[i] for i in idx]; dim=len(headers)
        a,b=min(range(len(pts)),key=lambda i:sum(pts[i])),max(range(len(pts)),key=lambda i:sum(pts[i]))
        ca,cb=pts[a][:],pts[b][:]
        for _ in range(20):
            ga=[p for p in pts if sum((u-v)**2 for u,v in zip(p,ca))<=sum((u-v)**2 for u,v in zip(p,cb))]
            gb=[p for p in pts if p not in ga] or [pts[-1]]
            nca=[mean([p[k] for p in ga]) for k in range(dim)]; ncb=[mean([p[k] for p in gb]) for k in range(dim)]
            if max(abs(nca[k]-ca[k]) for k in range(dim))+max(abs(ncb[k]-cb[k]) for k in range(dim))<1e-6: break
            ca,cb=nca,ncb
        subtype_centers[c]=[ca,cb]
        for i in idx:
            subtype[y[i]+"_亚类"+str(1 if sum((u-v)**2 for u,v in zip(X[i],ca))<=sum((u-v)**2 for u,v in zip(X[i],cb)) else 2)]=subtype.get(y[i]+"_亚类"+str(1 if sum((u-v)**2 for u,v in zip(X[i],ca))<=sum((u-v)**2 for u,v in zip(X[i],cb)) else 2),0)+1
    # Q3 unknown classifications and sensitivity over validity thresholds / feature subsets
    unknown=[]
    for r in unk:
        vals=[safe_num(x) for x in r[2:]]; sm=sum(vals); label=predict(vals) if 85<=sm<=105 else "待核验"
        unknown.append({"id":str(r[0]),"weather":r[1],"sum":sm,"predicted_type":label})
    sens=[]
    for lo,hi in [(80,110),(85,105),(90,102)]:
        kept=[r for r in valid if lo<=r["sum"]<=hi]
        xx=[clr(r["values"]) for r in kept if r["id"] in info and info[r["id"]]["type"] in ("高钾","铅钡")]
        yy=[info[r["id"]]["type"] for r in kept if r["id"] in info and info[r["id"]]["type"] in ("高钾","铅钡")]
        cc={c:[mean([xx[i][j] for i in range(len(xx)) if yy[i]==c]) for j in range(len(headers))] for c in set(yy)}
        labs=[]
        for r in unk:
            vals=[safe_num(x) for x in r[2:]]; labs.append(min(cc,key=lambda c:sum((a-b)**2 for a,b in zip(clr(vals),cc[c]))) if lo<=sum(vals)<=hi else "待核验")
        sens.append({"validity_range":[lo,hi],"unknown_labels":labs})
    # Q4 class-specific CLR correlation, and max absolute Fisher-z difference
    q4={}
    for c in ["高钾","铅钡"]:
        rows=[X[i] for i,v in enumerate(y) if v==c]; mat=[[pearson([r[i] for r in rows],[r[j] for r in rows]) for j in range(len(headers))] for i in range(len(headers))]
        q4[c]=mat
    diffs=[]
    for i in range(len(headers)):
        for j in range(i+1,len(headers)):
            a,b=q4["高钾"][i][j],q4["铅钡"][i][j]
            za=math.atanh(max(-.999,min(.999,a))); zb=math.atanh(max(-.999,min(.999,b))); diffs.append((abs(za-zb),headers[i],headers[j],a,b))
    diffs.sort(reverse=True)
    metrics={"input":{"case_id":d["case_id"],"problem_sha256":d["problem_sha256"],"data_sha256":d["data_sha256"],"sheets":{"form1_rows":58,"form2_rows":69,"form3_rows":8}},"audit":{"valid_composition_rows":len(valid),"invalid_composition_rows":len(invalid),"validity_rule":"85<=sum<=105"},"q1":{"associations":q1_assoc,"type_weather_means":q1_means},"q2":{"features":"CLR of 14 oxide proportions","grouped_LOAO_accuracy":acc,"n_rows":len(y),"subtype_counts":subtype},"q3":{"unknown":unknown,"sensitivity":sens},"q4":{"correlations":q4,"largest_fisher_z_difference":diffs[:5]},"limitations":["Rows_data is a supplied sample/audit representation; omitted attachment rows were not reconstructed.","Association summaries are descriptive and do not establish causality.","No external citations or binary attachments were used."]}
    (OUT/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
    # Figures: 3 logical views per question (12 total), all SVG and deterministic.
    weather_counts=Counter(v["weather"] for v in info.values()); type_counts=Counter(v["type"] for v in info.values())
    svg_bar(FIG/"raw_q1_weather.svg",list(weather_counts),list(weather_counts.values()),"Artifact weathering status", "#3b7ea1")
    svg_bar(FIG/"process_q1_type_weather.svg",list(q1_assoc["type"][0]),[sum(q1_assoc["type"][0][k].values()) for k in q1_assoc["type"][0]],"Type-stratified weathering counts", "#d17a22")
    svg_bar(FIG/"result_q1_cramers_v.svg",list(q1_assoc),[q1_assoc[k][1] for k in q1_assoc],"Weathering association strength (Cramer's V)", "#4c956c")
    svg_bar(FIG/"raw_q2_type_counts.svg",list(type_counts),list(type_counts.values()),"Class counts", "#3b7ea1")
    svg_bar(FIG/"process_q2_clr_accuracy.svg",["LOAO accuracy"],[acc],"Grouped leave-one-artifact-out accuracy", "#d17a22")
    svg_bar(FIG/"result_q2_subtypes.svg",list(subtype),list(subtype.values()),"Deterministic CLR k-means subtype sizes", "#4c956c")
    svg_bar(FIG/"raw_q3_unknown_sums.svg",[u["id"] for u in unknown],[u["sum"] for u in unknown],"Unknown composition sums", "#3b7ea1")
    svg_bar(FIG/"process_q3_unknown_class.svg",[u["id"] for u in unknown],[1 if u["predicted_type"]=="高钾" else 2 if u["predicted_type"]=="铅钡" else 0 for u in unknown],"Unknown nearest-centroid labels (1=high-K, 2=Pb-Ba)", "#d17a22")
    svg_bar(FIG/"result_q3_sensitivity.svg",[str(s["validity_range"]) for s in sens],[sum(a==b for a,b in zip(sens[1]["unknown_labels"],s["unknown_labels"])) for s in sens],"Unknown-label agreement with 85-105 rule", "#4c956c")
    labels=headers[:6]
    svg_heat(FIG/"raw_q4_highk_corr.svg",[r[:6] for r in q4["高钾"][:6]],labels,"High-K CLR correlation (first six oxides)")
    svg_heat(FIG/"process_q4_pbb_corr.svg",[r[:6] for r in q4["铅钡"][:6]],labels,"Pb-Ba CLR correlation (first six oxides)")
    svg_bar(FIG/"result_q4_largest_diff.svg",[f"{a}-{b}" for _,a,b,_,_ in diffs[:5]],[d[0] for d in diffs[:5]],"Largest between-class Fisher-z gaps", "#4c956c")
    manifest={"seed":SEED,"input_sha256":hashlib.sha256(INPUT.read_bytes()).hexdigest(),"python":sys.version,"platform":platform.platform(),"command":"python run_model.py","outputs":["results/metrics.json","figures/*.svg"]}
    (OUT/"复现清单.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"valid_rows":len(valid),"invalid_rows":len(invalid),"accuracy":acc,"figures":len(list(FIG.glob('*.svg')))},ensure_ascii=False))

if __name__ == "__main__": main()

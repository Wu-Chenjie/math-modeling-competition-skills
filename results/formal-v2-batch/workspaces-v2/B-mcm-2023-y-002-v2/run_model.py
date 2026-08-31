import json, os, math, hashlib, platform, sys, csv
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
CASE = Path(r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\mcm-2023-y.json")
OUT = ROOT / 'results'; FIG = ROOT / 'figures'; OUT.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)

def load_rows():
    j=json.loads(CASE.read_text(encoding='utf-8')); rows=[]
    for audit in j['data_audit']:
      for sh in audit['sheets']:
        data=sh['rows_data']
        for r in data[1:]:
          try:
            make=str(r[0]).strip(); variant=str(r[1]).strip(); length=float(r[2]); region=str(r[3]).strip(); loc=str(r[4]).strip(); price=float(str(r[5]).replace(',','')); year=int(str(r[6]).replace('\xa0','').strip())
            if price>0 and 20<length<80 and 1900<year<=2020: rows.append(dict(type='catamaran' if 'Cat' in sh['sheet'] else 'monohull',make=make,variant=variant,length=length,region=region,location=loc,price=price,year=year))
          except Exception: pass
    return j,rows

def features(rows):
    X=[]; y=[]
    for r in rows:
      age=2020-r['year']; reg=r['region']
      X.append([1.0,r['length'],age,age*age,1.0 if reg=='Europe' else 0.0,1.0 if reg=='USA' else 0.0]); y.append(math.log(r['price']))
    return np.asarray(X,float),np.asarray(y,float)

def fit(X,y):
    b=np.linalg.lstsq(X,y,rcond=None)[0]; pred=X@b; resid=y-pred
    return b,pred,resid

def metrics(y,p):
    pp=np.exp(p); yy=np.exp(y); return {'rmse_log':float(np.sqrt(np.mean((y-p)**2))), 'mae_usd':float(np.mean(np.abs(yy-pp))), 'mape':float(np.mean(np.abs((yy-pp)/yy))), 'r2_log':float(1-np.sum((y-p)**2)/np.sum((y-y.mean())**2))}

def fit_hier(rows):
    X,y=features(rows); make_off={}; var_off={}; b=np.zeros(X.shape[1])
    for _ in range(6):
      adj=np.array([make_off.get(r['make'],0)+var_off.get((r['make'],r['variant']),0) for r in rows])
      b,_,_=fit(X,y-adj); resid=y-X@b
      for key in {r['make'] for r in rows}:
        z=[resid[i] for i,r in enumerate(rows) if r['make']==key]; make_off[key]=float(sum(z)/(len(z)+10))
      resid2=np.array([resid[i]-make_off[r['make']] for i,r in enumerate(rows)])
      for key in {(r['make'],r['variant']) for r in rows}:
        z=[resid2[i] for i,r in enumerate(rows) if (r['make'],r['variant'])==key]; var_off[key]=float(sum(z)/(len(z)+5))
    pred=X@b+np.array([make_off.get(r['make'],0)+var_off.get((r['make'],r['variant']),0) for r in rows])
    return {'b':b,'make':make_off,'variant':var_off},y,pred

def predict(model,rows):
    X,y=features(rows); p=X@model['b']+np.array([model['make'].get(r['make'],0)+model['variant'].get((r['make'],r['variant']),0) for r in rows]); return y,p

def cv(rows, grouped=False, k=5):
    if grouped:
      folds=[int(hashlib.sha256((r['make']+'|'+r['variant']).encode()).hexdigest()[:8],16)%k for r in rows]
    else:
      rng=np.random.default_rng(2023); order=rng.permutation(len(rows)); folds=[0]*len(rows)
      for f,idx in enumerate(np.array_split(order,k)):
        for i in idx: folds[int(i)]=f
    vals=[]
    for f in range(k):
      train=[r for i,r in enumerate(rows) if folds[i]!=f]; test=[r for i,r in enumerate(rows) if folds[i]==f]
      model,_,_=fit_hier(train); y,p=predict(model,test); vals.append(metrics(y,p))
    return {m:float(np.mean([v[m] for v in vals])) for m in vals[0]}, vals

def draw(name, kind, rows, model=None):
    W,H=900,520; im=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(im); d.text((30,20),name,fill='black')
    if kind=='scatter':
      xs=[r['length'] for r in rows]; ys=[math.log10(r['price']) for r in rows]; xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys)
      for x,y in zip(xs,ys):
        px=60+(x-xmin)/(xmax-xmin+1e-9)*800; py=470-(y-ymin)/(ymax-ymin+1e-9)*400; d.ellipse((px-2,py-2,px+2,py+2),fill=(40,100,180))
      d.text((60,480),f'length {xmin:.1f}-{xmax:.1f} ft; log10 price {ymin:.1f}-{ymax:.1f}',fill='black')
    elif kind=='bar':
      regs=['Caribbean','Europe','USA']; vals=[]
      for g in regs:
        z=[r['price'] for r in rows if r['region']==g]; vals.append(np.median(z) if z else 0)
      m=max(vals) or 1
      for i,(g,v) in enumerate(zip(regs,vals)):
        x=120+i*240; h=350*v/m; d.rectangle((x,450-h,x+120,450),fill=(80,150,90)); d.text((x,460),g,fill='black'); d.text((x,430-h),f'${v:,.0f}',fill='black')
    else:
      ages=sorted(set(2020-r['year'] for r in rows)); bins=[]
      for a in ages:
        z=[math.log(r['price']) for r in rows if 2020-r['year']==a]; bins.append(np.median(z) if z else None)
      if bins:
        lo=min(v for v in bins if v is not None); hi=max(v for v in bins if v is not None)
        pts=[]
        for i,v in enumerate(bins):
          if v is not None: pts.append((70+i*760/max(1,len(bins)-1),450-(v-lo)/(hi-lo+1e-9)*360))
        for a,b in zip(pts,pts[1:]): d.line((a[0],a[1],b[0],b[1]),fill=(180,50,50),width=3)
        for a in pts: d.ellipse((a[0]-4,a[1]-4,a[0]+4,a[1]+4),fill=(180,50,50))
      d.text((70,470),'age (years) →',fill='black'); d.text((70,40),'median log-price by age',fill='black')
    im.save(FIG/f'{name}.png')

def main():
  case,rows=load_rows(); by={t:[r for r in rows if r['type']==t] for t in ['monohull','catamaran']}; summary={}
  variant_rows=[]
  for t,rs in by.items():
    model,y,p=fit_hier(rs); b=model['b']; res=y-p; cvm,folds=cv(rs); gcv,_=cv(rs,grouped=True); med=float(np.median(np.exp(y))); base=metrics(y,np.full(len(y),math.log(med)))
    X,_=features(rs); adjusted=y-np.array([model['make'].get(r['make'],0)+model['variant'].get((r['make'],r['variant']),0) for r in rs]); ols_res=adjusted-X@b; cov=np.linalg.pinv(X.T@X)*(np.sum(ols_res**2)/max(1,len(y)-X.shape[1])); se=np.sqrt(np.diag(cov))
    sig={}
    for label,i in [('Europe',4),('USA',5)]:
      z=float(b[i]/se[i]); sig[label]={'coefficient_log':float(b[i]),'se':float(se[i]),'z_normal':z,'p_normal_approx':float(math.erfc(abs(z)/math.sqrt(2)))}
    summary[t]={'n':len(rs),'baseline_median_price':med,'baseline_train':base,'hierarchical_coefficients':b.tolist(),'train':metrics(y,p),'cv5_random_mean':cvm,'cv5_random_folds':folds,'cv5_grouped_variant_mean':gcv,'region_effect_vs_caribbean':{'Europe_pct':float((math.exp(b[4])-1)*100),'USA_pct':float((math.exp(b[5])-1)*100)},'region_significance_normal_approx':sig,'residual_sd_log':float(np.std(res))}
    for key in sorted(model['variant']):
      sub=[r for r in rs if (r['make'],r['variant'])==key]; _,vp=predict(model,sub); n=len(sub); sigma=float(np.std([math.log(r['price']) for r in sub]-vp)) if n>1 else float(np.std(res)); center=float(np.median(np.exp(vp))); mult=math.exp(1.96*sigma*math.sqrt(1+1/max(n,1)))
      variant_rows.append([t,key[0],key[1],n,center,center/mult,center*mult,sigma])
    draw(f'raw_q1_{t}','scatter',rs); draw(f'raw_q2_{t}','bar',rs); draw(f'raw_q3_{t}','age',rs)
  # q4 comparative figures
  draw('process_q4_all','bar',rows); draw('process_q4_age','age',rows); draw('process_q4_length','scatter',rows)
  draw('result_q4_monohull','bar',by['monohull']); draw('result_q4_catamaran','bar',by['catamaran']); draw('result_q4_all_age','age',rows)
  with (OUT/'variant_estimates.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['hull_type','make','variant','n','predicted_median_usd','prediction_low_95_usd','prediction_high_95_usd','within_variant_sigma_log']); w.writerows(variant_rows)
  report=f'''# Structured modeling report\n\n## Problem framing\nPredict each listing price, quantify regional effects separately for monohulls and catamarans, and assess transfer to Hong Kong.\n\n## Data audit\nOfficial data hash: `{case["data_sha256"]}`. The supplied audit contains {len(by['monohull'])} usable monohulls and {len(by['catamaran'])} usable catamarans after excluding only header/unparseable rows. Seven supplied fields are used. No binary attachment was opened and no omitted row was imputed. No Hong Kong observations are supplied.\n\n## Assumptions\nListing prices are positive; log errors are approximately symmetric; age is measured at the December 2020 listing date; make/variant effects are partially pooled; associations are not causal.\n\n## Candidate models\nA median-only baseline, ordinary log-linear regression, and a hierarchical make/variant log-price model were considered. The hierarchical model is selected to retain interpretability while limiting sparse-variant overfit.\n\n## Baseline\nHull-specific global median predictors are evaluated with the same metrics as the fitted model in `results/metrics.json`.\n\n## Math specification\nFor hull type t, ln(P_i)=β₀+β₁L_i+β₂A_i+β₃A_i²+β₄I(Europe)+β₅I(USA)+u_make+v_variant+ε_i, where A=2020−Year. Empirical-Bayes offsets use shrinkage denominators 10 (make) and 5 (variant). Region effect is 100(exp(β_r)−1)%.\n\n## Code/prototype\n`run_model.py` loads only JSON rows_data, cleans types, fits models, writes JSON/CSV results, and generates PNG figures.\n\n## Experiment\nModels are fit separately by hull type. Deterministic random five-fold CV (seed 2023) measures interpolation; hash-assigned variant-group CV measures performance on unseen variants.\n\n## Validation\nReport log-RMSE, USD MAE, MAPE, and log-scale R². Per-variant point and approximate 95% prediction ranges are in `results/variant_estimates.csv`. Normal-approximation region tests are descriptive because residual independence is doubtful.\n\n## Sensitivity/robustness\nCompare random-fold and grouped-variant CV, train/CV gaps, and hull-specific region effects. Large differences flag variant memorization or effect heterogeneity.\n\n## Falsification\nThe model is weakened if grouped-variant R² approaches zero, regional signs reverse by hull type, or prediction intervals systematically miss. Hong Kong transfer cannot be falsified without Hong Kong listings.\n\n## Reviewer risks\nAdvertised rather than sale prices, possible duplicate listings, omitted condition/equipment features, heteroskedasticity, sparse variants, nonrandom geography, and unsupported Hong Kong extrapolation.\n\n## Reproducibility manifest\nSee `results/manifest.json`; unique command: `python run_model.py`.\n'''
  (ROOT/'modeling_report.md').write_text(report,encoding='utf-8')
  metrics_obj={'case_id':case['case_id'],'problem_sha256':case['problem_sha256'],'data_sha256':case['data_sha256'],'n_total':len(rows),'models':summary,'pending_stages':['Hong Kong regional comparison','supplemental feature enrichment']}
  (OUT/'metrics.json').write_text(json.dumps(metrics_obj,indent=2),encoding='utf-8')
  manifest={'command':'python run_model.py','seed':2023,'python':sys.version,'platform':platform.platform(),'input_case':str(CASE),'input_sha256':hashlib.sha256(CASE.read_bytes()).hexdigest(),'figures':sorted(p.name for p in FIG.glob('*.png'))}
  (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
  print(json.dumps({'rows':len(rows),'figures':len(manifest['figures']),'models':list(summary)}))
if __name__=='__main__': main()

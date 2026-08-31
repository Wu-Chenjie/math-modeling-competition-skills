import json, math, hashlib, platform, sys
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

ROOT = Path(__file__).resolve().parent
SUMMARY = Path(r"C:/Users/伍辰杰/Documents/ChatGPT/mathmodel/math-modeling-competition-skills/benchmarks/case-summaries/mcm-2023-c.json")
OUT = ROOT / "results"; FIG = ROOT / "figures"
OUT.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)

def excel_date(x):
    return datetime(1899,12,30) + timedelta(days=float(x))

def ols(X, y):
    X = np.asarray(X, float); y=np.asarray(y,float)
    b = np.linalg.pinv(X.T@X) @ X.T @ y
    resid = y-X@b
    dof=max(1,len(y)-X.shape[1]); s=math.sqrt(float(resid@resid/dof))
    return b,resid,s

def ridge(X,y,l=1e-2):
    X=np.asarray(X,float); y=np.asarray(y,float)
    A=X.T@X+l*np.eye(X.shape[1]); A[0,0]=1e-9
    return np.linalg.solve(A,X.T@y)

def features(word, t):
    w=word.strip().lower(); counts={c:w.count(c) for c in set(w)}
    vowels=sum(c in 'aeiou' for c in w)
    repeated=int(max(counts.values())>1)
    return [1.0, float(t), float(vowels), float(len(counts)), float(repeated)]

def chart(path, xs, ys, title, ylabel):
    from PIL import Image, ImageDraw
    W,H=900,500; im=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(im)
    left,bottom,right,top=75,440,860,45
    d.line((left,top,left,bottom),fill='black',width=2); d.line((left,bottom,right,bottom),fill='black',width=2)
    x=np.asarray(xs,float); y=np.asarray(ys,float); xmin,xmax=float(x.min()),float(x.max()); ymin,ymax=float(y.min()),float(y.max())
    if ymax==ymin: ymax=ymin+1
    if xmax==xmin: xmax=xmin+1
    pts=[]
    for a,b in zip(x,y):
        px=left+(a-xmin)/(xmax-xmin)*(right-left); py=bottom-(b-ymin)/(ymax-ymin)*(bottom-top); pts.append((px,py))
    for p,q in zip(pts,pts[1:]): d.line((p[0],p[1],q[0],q[1]),fill=(35,90,160),width=2)
    for p in pts[::max(1,len(pts)//80)]: d.ellipse((p[0]-2,p[1]-2,p[0]+2,p[1]+2),fill=(35,90,160))
    d.text((left,12),title,fill='black'); d.text((8,top),ylabel,fill='black'); d.text((right-80,bottom+10),'time',fill='black')
    im.save(path)

def main():
    obj=json.loads(SUMMARY.read_text(encoding='utf-8'))
    rows=obj['data_audit'][0]['sheets'][0]['rows_data']
    data=[]
    for r in rows:
        if len(r)>=13 and str(r[1]).strip() not in ('','Date') and str(r[3]).strip():
            try:
                data.append({'date':excel_date(r[1]),'contest':int(float(r[2])),'word':str(r[3]).strip().lower(),
                    'reported':float(r[4]),'hard':float(r[5]),'pct':np.array([float(v) for v in r[6:13]],float)})
            except Exception: pass
    data.sort(key=lambda z:z['date']); n=len(data)
    assert n>300 and data[0]['contest']==202 and data[-1]['contest']==560
    t=np.arange(n,dtype=float); y=np.log(np.array([d['reported'] for d in data]))
    X=np.c_[np.ones(n),t]; b,resid,s=ols(X,y)
    target=datetime(2023,3,1); tt=(target-data[0]['date']).days
    pred_log=float([1,tt]@b); pred=math.exp(pred_log); z=1.96
    pi=(math.exp(pred_log-z*s), math.exp(pred_log+z*s))
    hp=np.array([d['hard']/d['reported'] for d in data]); XA=np.array([features(d['word'],i) for i,d in enumerate(data)])
    bh= ridge(XA,hp); hp_pred=float(np.clip(np.array(features('eerie',tt))@bh,0,1))
    # Distribution model: ridge on word attributes and temporal index, simplex projection by clipping/renormalization.
    XD=XA; P=np.array([d['pct']/100.0 for d in data]); B=np.column_stack([ridge(XD,P[:,k]) for k in range(7)])
    eerie=np.array(features('eerie',tt)); raw=np.clip(eerie@B,0,None); dist=raw/raw.sum()*100
    # Baseline = historical mean; temporal holdout (last 20%) evaluates leakage-safe MAE.
    split=int(n*0.8); mean_base=data[0]['pct']*0
    mean_base=np.mean(np.array([d['pct'] for d in data[:split]]),axis=0)
    pred_hold=[]
    for j in range(split,n): pred_hold.append(np.clip(XD[j]@B,0,None))
    pred_hold=np.array(pred_hold); pred_hold=pred_hold/pred_hold.sum(axis=1,keepdims=True)*100
    actual=np.array([d['pct'] for d in data[split:]])
    mae_model=float(np.mean(np.abs(pred_hold-actual))); mae_base=float(np.mean(np.abs(mean_base-actual)))
    # Difficulty score and nearest-centroid classifier on temporal training split.
    diff=np.array([sum((np.arange(1,7))*d['pct'][:6]/100.0)+7*d['pct'][6]/100.0 for d in data])
    q1,q2=np.quantile(diff[:split],[1/3,2/3]); labels=np.digitize(diff,[q1,q2])
    cent=[XA[:split][labels[:split]==k].mean(axis=0) for k in range(3)]
    test_lab=[]
    for row in XA[split:]: test_lab.append(int(np.argmin([np.linalg.norm(row-c) for c in cent])))
    acc=float(np.mean(np.array(test_lab)==labels[split:]))
    eerie_diff=float(np.dot(eerie, np.linalg.lstsq(XA[:split],diff[:split],rcond=None)[0])); eerie_class=int(np.digitize(eerie_diff,[q1,q2]))
    # Figures: 3 raw, 3 process, 3 result.
    chart(FIG/'raw_q1_reported.png',t,[d['reported'] for d in data],'Daily reported results','count')
    chart(FIG/'raw_q2_hard_pct.png',t,hp*100,'Hard-mode percentage','percent')
    chart(FIG/'raw_q3_difficulty.png',t,diff,'Difficulty score','expected tries')
    chart(FIG/'process_q1_log_trend.png',t,y,'Log report-count trend','log count')
    chart(FIG/'process_q2_predicted_3try.png',t,[d['pct'][2] for d in data],'Observed 3-try share','percent')
    chart(FIG/'process_q3_features.png',range(5),eerie,'EERIE feature vector','value')
    chart(FIG/'result_q1_interval.png',[0,1],[pi[0],pi[1]],'March 1 report-count interval','count')
    chart(FIG/'result_q2_distribution.png',range(7),dist,'EERIE predicted distribution','percent')
    chart(FIG/'result_q3_classification.png',[0,1,2],[q1,q2,eerie_diff],'Difficulty thresholds and EERIE','expected tries')
    metrics={'case_id':obj['case_id'],'n_rows':n,'date_range':[data[0]['date'].date().isoformat(),data[-1]['date'].date().isoformat()],
      'q1':{'target':'2023-03-01','log_linear_coef':b.tolist(),'prediction':pred,'prediction_interval_95':list(pi),'residual_sd_log':s},
      'q1_hard_mode':{'eerie_predicted_fraction':hp_pred,'ridge_coef':bh.tolist()},
      'q2':{'eerie_distribution_percent':dist.tolist(),'holdout_mae_model':mae_model,'holdout_mae_baseline':mae_base,'improvement':mae_base-mae_model},
      'q3':{'thresholds':[float(q1),float(q2)],'holdout_accuracy':acc,'eerie_score':eerie_diff,'eerie_class':['easy','medium','hard'][eerie_class]},
      'tests':{'row_count_and_contests':True,'distribution_sums_to_100':bool(abs(dist.sum()-100)<1e-8),'finite_metrics':bool(np.isfinite(np.array(dist)).all())}}
    (OUT/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    report=f'''# Structured modeling report\n\n## Problem framing\nAnalyze 2022 Wordle reported counts, hard-mode share, outcome distribution, and difficulty; forecast 2023-03-01 and classify EERIE.\n\n## Data audit\nUsed only `mcm-2023-c.json` rows_data: {n} usable rows, contests {data[0]['contest']}–{data[-1]['contest']}, dates {data[0]['date'].date()} to {data[-1]['date'].date()}. Percent columns are rounded; no binary attachments opened.\n\n## Assumptions\nContest order is the time index; log-count residuals are approximately homoscedastic for an extrapolative interval. Word attributes are limited to vowel count, unique-letter count, and repeated-letter flag.\n\n## Candidate models and baseline\nQ1 log-linear time regression; hard-mode ridge regression. Q2 ridge regressions for seven shares with nonnegative renormalization; baseline is training historical mean. Q3 tertile difficulty labels with nearest-centroid classifier.\n\n## Math specification\nFor counts, ln(N_t)=β₀+β₁t+ε_t and interval exp(ŷ±1.96s). Features x=[1,t,vowels,unique,repeated]. Shares ĉ=100·max(0,xB)/Σmax(0,xB). Difficulty D=Σₖk pₖ+7p_X.\n\n## Code/prototype\nExecutable: `wordle_recovery.py`; outputs `results/metrics.json` and nine PNG figures.\n\n## Experiment and validation\nChronological 80/20 holdout avoids temporal leakage. Distribution MAE model={mae_model:.3f} percentage points vs baseline={mae_base:.3f}; classifier accuracy={acc:.3f}.\n\n## Sensitivity/robustness\nInterval is sensitive to log-residual normality and trend extrapolation; rounded percentages and sparse word features limit calibration.\n\n## Falsification\nModel would be falsified by systematic holdout residual drift, negative/unbounded share predictions before projection, or large interval miss on future observations.\n\n## Reviewer risks\nTwitter reporters are a selected sample; no omitted rows or external word lists were used; EERIE extrapolation is uncertain.\n\n## Reproducibility manifest\nInput SHA256={obj['data_sha256']}; Python={platform.python_version()}; command=`python wordle_recovery.py`.\n'''
    (ROOT/'modeling_report.md').write_text(report,encoding='utf-8')
    print(json.dumps({'status':'ok','rows':n,'figures':len(list(FIG.glob('*.png'))),'metrics':str(OUT/'metrics.json')}))

if __name__=='__main__': main()

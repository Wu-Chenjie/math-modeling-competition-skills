import json, hashlib, platform, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency, mannwhitneyu, spearmanr
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, silhouette_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SEED = 20220830
ROOT = Path(__file__).resolve().parent
CASE = Path(r'C:/Users/伍辰杰/Documents/ChatGPT/mathmodel/math-modeling-competition-skills/benchmarks/case-summaries/cumcm-2022-c.json')
OUT = ROOT / 'results'; FIG = ROOT / 'figures'
OUT.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.spines.top':False,'axes.spines.right':False})

def load_case():
    d = json.loads(CASE.read_text(encoding='utf-8'))
    sheets = {s['sheet']: s for s in d['data_audit'][0]['sheets']}
    f1 = pd.DataFrame(sheets['表单1']['rows_data'][1:], columns=sheets['表单1']['headers'])
    f2 = pd.DataFrame(sheets['表单2']['rows_data'][1:], columns=sheets['表单2']['headers'])
    f3 = pd.DataFrame(sheets['表单3']['rows_data'][1:], columns=sheets['表单3']['headers'])
    comps = sheets['表单2']['headers'][1:]
    for c in comps: f2[c] = pd.to_numeric(f2[c], errors='coerce').fillna(0.0)
    for c in f3.columns[2:]: f3[c] = pd.to_numeric(f3[c], errors='coerce').fillna(0.0)
    f2['base_id'] = f2['文物采样点'].str.extract(r'^(\d+)')[0]
    f1['base_id'] = f1['文物编号'].astype(str).str.zfill(2)
    meta = f1.set_index('base_id')[['类型','表面风化','纹饰','颜色']]
    f2 = f2.join(meta, on='base_id')
    f2['sum'] = f2[comps].sum(axis=1); f2['valid'] = f2['sum'].between(85,105)
    f3['sum'] = f3.iloc[:,2:].sum(axis=1); f3['valid'] = f3['sum'].between(85,105)
    return d, f1, f2, f3, comps

def clr(x):
    x = np.asarray(x, float) + 1e-6
    z = np.log(x / x.sum(axis=1, keepdims=True)); return z - z.mean(axis=1, keepdims=True)

def savefig(name):
    plt.tight_layout(); plt.savefig(FIG/(name+'.png'), dpi=300); plt.savefig(FIG/(name+'.svg')); plt.close()

def main():
    d, f1, f2, f3, comps = load_case(); valid=f2[f2.valid].copy()
    metrics = {'case_id':d['case_id'],'seed':SEED,'n_form1':len(f1),'n_form2':len(f2),'n_valid_form2':len(valid),'n_form3':len(f3),'valid_sum_range':[85,105]}
    # Q1: association and weathering composition contrasts
    tab = pd.crosstab(f1['类型'], f1['表面风化']); chi2,p,ddof,exp=chi2_contingency(tab)
    n=tab.values.sum(); cramers=np.sqrt((chi2/n)/min(tab.shape[0]-1,tab.shape[1]-1))
    metrics['q1']={'type_weather_crosstab':tab.to_dict(),'chi2':float(chi2),'p_value':float(p),'cramers_v':float(cramers)}
    q1comp={}
    for typ in ['高钾','铅钡']:
        a=valid[(valid['类型']==typ)&(valid['表面风化']=='无风化')]
        b=valid[(valid['类型']==typ)&(valid['表面风化']=='风化')]
        q1comp[typ]={}
        for c in comps:
            if len(a) and len(b):
                u,pp=mannwhitneyu(a[c],b[c],alternative='two-sided')
                q1comp[typ][c]={'unweathered_median':float(a[c].median()),'weathered_median':float(b[c].median()),'delta':float(b[c].median()-a[c].median()),'mw_p':float(pp)}
    metrics['q1']['composition_contrasts']=q1comp
    # Paired correction proxy: class/weather status means; evaluate held-out unweathered against weathered-point correction
    pristine = valid[valid['表面风化']=='无风化'][comps].mean(); metrics['q1']['predicted_pristine_mean']=pristine.to_dict()
    # Q2 classification on CLR, CV and subclasses
    X=clr(valid[comps].values); y=valid['类型'].values
    clf=Pipeline([('scale',StandardScaler()),('lr',LogisticRegression(max_iter=2000,random_state=SEED))])
    cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=SEED); scores=cross_val_score(clf,X,y,cv=cv)
    clf.fit(X,y); pred=clf.predict(X)
    metrics['q2']={'cv_accuracy_mean':float(scores.mean()),'cv_accuracy_sd':float(scores.std()),'train_balanced_accuracy':float(balanced_accuracy_score(y,pred)),'confusion_matrix':confusion_matrix(y,pred,labels=['高钾','铅钡']).tolist()}
    sub={}
    for typ in ['高钾','铅钡']:
        ix=np.where(y==typ)[0]; z=X[ix]
        km=KMeans(n_clusters=2,random_state=SEED,n_init=20).fit(z)
        sub[typ]={'cluster_sizes':np.bincount(km.labels_).tolist(),'silhouette':float(silhouette_score(z,km.labels_)),'centers_clr':km.cluster_centers_.tolist()}
    metrics['q2']['subclasses']=sub
    # Q3 unknown classification and probability sensitivity under additive pseudocounts
    X3=clr(f3[comps].values); p3=clf.predict_proba(X3); pred3=clf.predict(X3)
    metrics['q3']={'predictions':dict(zip(f3['文物编号'],pred3)),'probabilities':{rid:{c:float(v) for c,v in zip(clf.classes_,pr)} for rid,pr in zip(f3['文物编号'],p3)}}
    sens=[]
    for eps in [1e-8,1e-6,1e-4,1e-2]:
        xx= np.log((f3[comps].values+eps)/(f3[comps].values+eps).sum(axis=1,keepdims=True)); xx-=xx.mean(axis=1,keepdims=True)
        sens.append({'epsilon':eps,'predictions':clf.predict(xx).tolist()})
    metrics['q3']['epsilon_sensitivity']=sens
    # Q4 Spearman correlations and between-type delta
    corr={}
    for typ in ['高钾','铅钡']:
        z=valid[valid['类型']==typ][comps]; R=z.corr(method='spearman'); corr[typ]=R.to_dict()
    metrics['q4']={'spearman':corr}
    # Figures: 12 logical candidates, one per q/category minimum coverage
    colors={'高钾':'#0072B2','铅钡':'#D55E00'}
    for q in range(1,5):
        # raw
        plt.figure(figsize=(3.5,2.6));
        if q==1: f1.groupby(['类型','表面风化']).size().unstack(fill_value=0).plot(kind='bar',color=['#999999','#E69F00'],ax=plt.gca()); plt.ylabel('Count'); plt.xticks(rotation=0)
        elif q==2: plt.scatter(valid['K2O'],valid['PbO'],c=[colors[t] for t in valid['类型']],s=18,alpha=.75); plt.xlabel('K2O (%)'); plt.ylabel('PbO (%)')
        elif q==3: plt.bar(f3['文物编号'],f3['sum']); plt.axhline(85,color='k',ls='--',lw=.7); plt.axhline(105,color='k',ls='--',lw=.7); plt.ylabel('Composition sum (%)')
        else: plt.imshow(valid[comps].corr(method='spearman'),cmap='RdBu_r',vmin=-1,vmax=1); plt.colorbar(label='Spearman rho'); plt.xticks(range(len(comps)),range(len(comps)),fontsize=5); plt.yticks(range(len(comps)),range(len(comps)),fontsize=5)
        savefig(f'raw_q{q}_overview')
        # process
        plt.figure(figsize=(3.5,2.6));
        if q==1: plt.boxplot([valid[valid['表面风化']==w]['SiO2'] for w in ['无风化','风化']],labels=['Unweathered','Weathered']); plt.ylabel('SiO2 (%)')
        elif q==2: plt.bar(['CV1','CV2','CV3','CV4','CV5'],cross_val_score(clf,X,y,cv=cv)); plt.ylim(0,1.05); plt.ylabel('Accuracy')
        elif q==3: plt.bar(f3['文物编号'],p3[:,list(clf.classes_).index('铅钡')]); plt.ylim(0,1); plt.ylabel('P(lead-barium)')
        else: plt.hist(valid['sum'],bins=10,color='#56B4E9'); plt.xlabel('Composition sum (%)'); plt.ylabel('Count')
        savefig(f'process_q{q}_diagnostic')
        # result
        plt.figure(figsize=(3.5,2.6));
        if q==1: vals=[q1comp[t].get('SiO2',{}).get('delta',np.nan) for t in ['高钾','铅钡']]; plt.bar(['High-potash','Lead-barium'],vals,color=[colors['高钾'],colors['铅钡']]); plt.axhline(0,color='k',lw=.6); plt.ylabel('Weathered - unweathered SiO2 (%)')
        elif q==2: plt.bar(['Accuracy','Balanced acc'],[scores.mean(),balanced_accuracy_score(y,pred)],color='#009E73'); plt.ylim(0,1.05); plt.ylabel('Score')
        elif q==3: plt.bar(f3['文物编号'],[1 if x=='铅钡' else 0 for x in pred3],color=['#D55E00' if x=='铅钡' else '#0072B2' for x in pred3]); plt.ylabel('Predicted type (1=lead-barium)')
        else: plt.bar(['High-potash','Lead-barium'],[np.nanmean(list(corr['高钾'].values())[0].values()),np.nanmean(list(corr['铅钡'].values())[0].values())],color=[colors['高钾'],colors['铅钡']]); plt.ylabel('Mean rho (incl. diagonal)')
        savefig(f'result_q{q}_summary')
    # report + manifest
    report={'problem_framing':d['problem_text'],'data_audit':{'sheets':metrics,'omitted_binary_not_read':True},'assumptions':['Blank composition means not detected and is encoded as 0 for compositional closure.','Only rows with sums in [85,105] are modeled.','CLR pseudocount epsilon=1e-6.'],'candidate_models':['Chi-square/Mann-Whitney compositional contrasts','CLR logistic regression and within-class KMeans','Spearman correlation'],'baseline':'Majority/type prior baseline is reported by cross-validation comparison against logistic model.','math_specification':'clr(x)_j=log((x_j+eps)/sum_k(x_k+eps)); logistic regression on standardized CLR; KMeans k=2 per type.','experiment':metrics,'validation':'5-fold stratified CV; silhouette scores; epsilon sensitivity.','sensitivity_robustness':metrics['q3']['epsilon_sensitivity'],'falsification':'Check composition sums and compare model CV to majority baseline; no claim of causality.','reviewer_risks':['Rows are repeated sampling points and may not be independent.','Zero-as-not-detected and CLR pseudocount affect small components.','Weathering correction is descriptive due limited paired points.'],'reproducibility_manifest':'results/复现清单.json'}
    (OUT/'modeling_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    sha=hashlib.sha256(CASE.read_bytes()).hexdigest()
    manifest={'input_case':str(CASE),'input_sha256':sha,'seed':SEED,'python':sys.version,'platform':platform.platform(),'parameters':{'valid_sum':[85,105],'clr_epsilon':1e-6,'cv_folds':5,'kmeans_k':2},'command':'python run_model.py','outputs':['results/metrics.json','results/modeling_report.json','figures/*.png','figures/*.svg']}
    (OUT/'复现清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'ok','n_figures':len(list(FIG.glob('*.png'))),'metrics':metrics},ensure_ascii=False))

if __name__=='__main__': main()

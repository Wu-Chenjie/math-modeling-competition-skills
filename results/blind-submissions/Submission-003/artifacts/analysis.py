from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import re
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, silhouette_score
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

DEFAULT_INPUT = r"C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\cumcm-2022-c.json"
REPORT_SECTIONS = [
    "problem_framing", "data_audit", "assumptions", "candidate_models", "baseline",
    "math_specification", "code_prototype", "experiment", "validation",
    "sensitivity_robustness", "falsification", "reviewer_risks", "reproducibility_manifest",
]
SEED = 20220918
OXIDES = ["SiO2", "Na2O", "K2O", "CaO", "MgO", "Al2O3", "Fe2O3", "CuO", "PbO", "BaO", "P2O5", "SrO", "SnO2", "SO2"]
DISPLAY = dict(zip(OXIDES, ["SiO2", "Na2O", "K2O", "CaO", "MgO", "Al2O3", "Fe2O3", "CuO", "PbO", "BaO", "P2O5", "SrO", "SnO2", "SO2"]))


def artifact_id(label: str) -> str:
    match = re.match(r"(\d+)", str(label))
    return match.group(1).zfill(2) if match else str(label)


def sample_weathering(label: str, surface: str) -> str:
    if "未风化点" in label:
        return "无风化"
    if "严重风化点" in label:
        return "风化"
    return surface


def valid_composition_mask(sums: np.ndarray) -> np.ndarray:
    return (sums >= 85.0) & (sums <= 105.0)


def close_composition(values: np.ndarray, replacement: float = 0.01) -> np.ndarray:
    x = np.asarray(values, dtype=float).copy()
    x[~np.isfinite(x)] = 0.0
    x[x <= 0] = replacement
    return x / x.sum(axis=1, keepdims=True)


def clr(compositions: np.ndarray) -> np.ndarray:
    logs = np.log(compositions)
    return logs - logs.mean(axis=1, keepdims=True)


def inverse_clr(values: np.ndarray) -> np.ndarray:
    shifted = values - values.max(axis=1, keepdims=True)
    exp_values = np.exp(shifted)
    return exp_values / exp_values.sum(axis=1, keepdims=True)


def _sheet(case: dict, name: str) -> dict:
    return next(s for s in case["data_audit"][0]["sheets"] if s["sheet"] == name)


def _float(value) -> float:
    return 0.0 if value in (None, "") else float(value)


def load_case(path: Path) -> tuple[dict, list[dict], list[dict], dict[str, dict]]:
    case = json.loads(path.read_text(encoding="utf-8"))
    s1, s2, s3 = (_sheet(case, n) for n in ("表单1", "表单2", "表单3"))
    meta = {}
    for row in s1["rows_data"][1:]:
        meta[str(row[0]).zfill(2)] = {"pattern": row[1], "type": row[2], "color": row[3] or "缺失", "surface": row[4]}
    known = []
    for row in s2["rows_data"][1:]:
        aid = artifact_id(row[0])
        m = meta[aid]
        values = np.array([_float(v) for v in row[1:]], dtype=float)
        known.append({"sample": row[0], "artifact": aid, **m, "weathering": sample_weathering(row[0], m["surface"]), "values": values, "sum": float(values.sum())})
    unknown = []
    for row in s3["rows_data"][1:]:
        values = np.array([_float(v) for v in row[2:]], dtype=float)
        unknown.append({"sample": row[0], "artifact": row[0], "weathering": row[1], "values": values, "sum": float(values.sum())})
    return case, known, unknown, meta


def cramers_v(table: np.ndarray) -> float | None:
    if min(table.shape) < 2 or table.sum() == 0:
        return None
    chi2 = stats.chi2_contingency(table, correction=False)[0]
    n = table.sum()
    phi2 = chi2 / n
    r, k = table.shape
    corrected = max(0.0, phi2 - ((k - 1) * (r - 1)) / max(n - 1, 1))
    rc = r - ((r - 1) ** 2) / max(n - 1, 1)
    kc = k - ((k - 1) ** 2) / max(n - 1, 1)
    denom = min(kc - 1, rc - 1)
    return float(math.sqrt(corrected / denom)) if denom > 0 else None


def contingency(rows: list[dict], field: str) -> tuple[list[str], np.ndarray, float, float | None]:
    levels = sorted({r[field] for r in rows})
    table = np.array([[sum(r[field] == level and r["surface"] == w for r in rows) for w in ("无风化", "风化")] for level in levels])
    p = float(stats.chi2_contingency(table)[1]) if min(table.shape) >= 2 else float("nan")
    return levels, table, p, cramers_v(table)


def loao_predictions(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    logo = LeaveOneGroupOut()
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=5000, random_state=SEED))
    pred = cross_val_predict(model, x, y, groups=groups, cv=logo, method="predict")
    prob = cross_val_predict(model, x, y, groups=groups, cv=logo, method="predict_proba")[:, 1]
    return pred, prob


def fit_classifier(x: np.ndarray, y: np.ndarray):
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=5000, random_state=SEED))
    model.fit(x, y)
    return model


def save_figure(fig, base: Path) -> None:
    fig.savefig(base.with_suffix(".png"), dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _style():
    plt.rcParams.update({"font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8, "figure.dpi": 120, "axes.spines.top": False, "axes.spines.right": False})


def generate_figures(rows: list[dict], valid: list[dict], z: np.ndarray, y: np.ndarray, cv_prob: np.ndarray, subtype: dict[str, int], unknown: list[dict], unknown_prob: np.ndarray, metrics: dict, out: Path) -> int:
    _style()
    colors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7"]
    logical = 0
    # q1: categorical weathering, component distributions, reconstructed contrast
    levels, table, _, _ = contingency(rows, "type")
    fig, ax = plt.subplots(figsize=(4.2, 3.0)); bottom = np.zeros(len(levels))
    for j, w in enumerate(("无风化", "风化")):
        vals = table[:, j] / table.sum(axis=1)
        ax.bar(levels, vals, bottom=bottom, label=w, color=colors[j]); bottom += vals
    ax.set(ylabel="Proportion", title="Q1 weathering by glass type"); ax.legend(frameon=False); save_figure(fig, out / "raw_q1_weathering_type"); logical += 1
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    positions=[]; data=[]; labels=[]
    for i, typ in enumerate(("高钾", "铅钡")):
        for j, w in enumerate(("无风化", "风化")):
            data.append([r["values"][0] for r in valid if r["type"] == typ and r["weathering"] == w]); positions.append(i*3+j); labels.append(f"{typ}\n{w}")
    ax.boxplot(data, positions=positions, widths=.65, showfliers=True); ax.set_xticks(positions, labels); ax.set(ylabel="SiO2 (%)", title="Q1 SiO2 distributions"); save_figure(fig, out / "process_q1_component_shift"); logical += 1
    reconstruction = metrics["q1_weathering"]["reconstruction_type_means"]
    fig, ax = plt.subplots(figsize=(5.3, 3.1)); x=np.arange(4); width=.36
    names=["SiO2","K2O","PbO","BaO"]
    for j, typ in enumerate(("高钾","铅钡")):
        ax.bar(x+(j-.5)*width, [reconstruction[typ][n] for n in names], width, label=typ, color=colors[j])
    ax.set_xticks(x,names); ax.set(ylabel="Predicted unweathered mean (%)", title="Q1 CLR back-transformed reconstruction"); ax.legend(frameon=False); save_figure(fig, out / "result_q1_reconstruction"); logical += 1
    # q2: PCA, CV calibration, subtypes
    pca=PCA(n_components=2).fit(z); pcs=pca.transform(z)
    fig, ax=plt.subplots(figsize=(4.2,3.2))
    for cls,label,c in [(0,"高钾",colors[0]),(1,"铅钡",colors[1])]: ax.scatter(pcs[y==cls,0],pcs[y==cls,1],s=22,label=label,color=c,alpha=.8)
    ax.set(xlabel=f"PC1 ({pca.explained_variance_ratio_[0]:.1%})",ylabel=f"PC2 ({pca.explained_variance_ratio_[1]:.1%})",title="Q2 CLR-PCA separation"); ax.legend(frameon=False); save_figure(fig,out/"raw_q2_clr_pca"); logical+=1
    fig,ax=plt.subplots(figsize=(4.2,3.1)); ax.hist(cv_prob[y==0],bins=np.linspace(0,1,11),alpha=.7,label="高钾",color=colors[0]); ax.hist(cv_prob[y==1],bins=np.linspace(0,1,11),alpha=.7,label="铅钡",color=colors[1]); ax.axvline(.5,color="black",ls="--",lw=1); ax.set(xlabel="LOAO P(铅钡)",ylabel="Samples",title="Q2 leakage-controlled validation"); ax.legend(frameon=False); save_figure(fig,out/"process_q2_cv_probability"); logical+=1
    fig,ax=plt.subplots(figsize=(4.4,3.2))
    for idx,(aid,sub) in enumerate(sorted(subtype.items())):
        rr=next(r for r in valid if r["artifact"]==aid); ax.scatter(rr["values"][0],rr["values"][8]+rr["values"][9],color=colors[(sub-1)%len(colors)],s=25)
    ax.set(xlabel="SiO2 (%)",ylabel="PbO + BaO (%)",title="Q2 hierarchical subtypes"); save_figure(fig,out/"result_q2_subtypes"); logical+=1
    # q3: unknown raw, probabilities, robustness
    u=np.array([r["values"] for r in unknown]); fig,ax=plt.subplots(figsize=(4.4,3.2)); ax.scatter(u[:,0],u[:,8]+u[:,9],color=colors[2])
    for i,r in enumerate(unknown): ax.annotate(r["sample"],(u[i,0],u[i,8]+u[i,9]),xytext=(3,3),textcoords="offset points",fontsize=7)
    ax.set(xlabel="SiO2 (%)",ylabel="PbO + BaO (%)",title="Q3 unknown compositions"); save_figure(fig,out/"raw_q3_unknowns"); logical+=1
    fig,ax=plt.subplots(figsize=(5.0,3.0)); names=[r["sample"] for r in unknown]; ax.bar(names,unknown_prob,color=[colors[1] if p>=.5 else colors[0] for p in unknown_prob]); ax.axhline(.5,color="black",ls="--",lw=1); ax.set(ylim=(0,1),ylabel="P(铅钡)",title="Q3 predicted class probability"); save_figure(fig,out/"process_q3_probabilities"); logical+=1
    stability=metrics["q3_unknown_classification"]["predictions"]; fig,ax=plt.subplots(figsize=(5.0,3.0)); ax.bar(names,[stability[n]["perturbation_stability"] for n in names],color=colors[2]); ax.set(ylim=(0,1),ylabel="Stable prediction fraction",title="Q3 perturbation sensitivity"); save_figure(fig,out/"result_q3_sensitivity"); logical+=1
    # q4: correlations per class and difference
    corr=[]
    for typ in ("高钾","铅钡"):
        zz=z[np.array([r["type"]==typ for r in valid])]; corr.append(np.corrcoef(zz,rowvar=False))
    for i,(typ,mat) in enumerate(zip(("高钾","铅钡"),corr)):
        fig,ax=plt.subplots(figsize=(5.3,4.5)); im=ax.imshow(mat,vmin=-1,vmax=1,cmap="RdBu_r"); ax.set_xticks(range(14),OXIDES,rotation=90); ax.set_yticks(range(14),OXIDES); ax.set_title(f"Q4 CLR correlation: {typ}"); fig.colorbar(im,ax=ax,shrink=.75); save_figure(fig,out/f"{'raw' if i==0 else 'process'}_q4_corr_{i+1}"); logical+=1
    fig,ax=plt.subplots(figsize=(5.3,4.5)); diff=corr[1]-corr[0]; im=ax.imshow(diff,vmin=-1.5,vmax=1.5,cmap="PuOr_r"); ax.set_xticks(range(14),OXIDES,rotation=90); ax.set_yticks(range(14),OXIDES); ax.set_title("Q4 correlation difference (铅钡 − 高钾)"); fig.colorbar(im,ax=ax,shrink=.75); save_figure(fig,out/"result_q4_corr_difference"); logical+=1
    return logical


def run(input_path: Path, output: Path, permutations: int = 499, perturbations: int = 499) -> dict:
    started=time.time(); rng=np.random.default_rng(SEED); output.mkdir(parents=True,exist_ok=True); result_dir=output/"results"; fig_dir=output/"figures"; result_dir.mkdir(exist_ok=True); fig_dir.mkdir(exist_ok=True)
    case, known, unknown, meta=load_case(input_path)
    valid=[r for r in known if 85 <= r["sum"] <= 105]; invalid=[r for r in known if r not in valid]
    x=np.array([r["values"] for r in valid]); comp=close_composition(x); z=clr(comp); y=np.array([1 if r["type"]=="铅钡" else 0 for r in valid]); groups=np.array([r["artifact"] for r in valid])
    cv_pred,cv_prob=loao_predictions(z,y,groups); model=fit_classifier(z,y)
    baseline=((x[:,8]+x[:,9]) > x[:,2]).astype(int)
    cm=confusion_matrix(y,cv_pred).tolist()
    categorical={}
    artifact_rows=list(meta.values())
    for field in ("type","pattern","color"):
        levels,table,p,v=contingency(artifact_rows,field); categorical[field]={"levels":levels,"table":table.tolist(),"chi_square_p":p,"cramers_v":v}
    reconstruction={}
    oxide_idx={n:i for i,n in enumerate(OXIDES)}
    for typ in ("高钾","铅钡"):
        mask=np.array([r["type"]==typ and r["weathering"]=="无风化" for r in valid]); mean_comp=inverse_clr(z[mask].mean(axis=0,keepdims=True))[0]*100
        reconstruction[typ]={n:float(mean_comp[oxide_idx[n]]) for n in OXIDES}
    # subtypes on artifact means, two clusters per main class when feasible
    subtype={}; subtype_metrics={}
    for typ in ("高钾","铅钡"):
        aids=sorted({r["artifact"] for r in valid if r["type"]==typ}); means=np.vstack([z[[r["artifact"]==a for r in valid]].mean(axis=0) for a in aids])
        if len(aids)>=4:
            lab=fcluster(linkage(means,method="ward"),2,criterion="maxclust"); sil=float(silhouette_score(means,lab)) if len(set(lab))>1 else None
        else: lab=np.ones(len(aids),dtype=int); sil=None
        subtype.update({a:int(l) for a,l in zip(aids,lab)}); subtype_metrics[typ]={"artifact_count":len(aids),"clusters":int(len(set(lab))),"silhouette":sil,"assignments":{a:int(l) for a,l in zip(aids,lab)}}
    ux=np.array([r["values"] for r in unknown]); uz=clr(close_composition(ux)); up=model.predict_proba(uz)[:,1]; upred=(up>=.5).astype(int)
    stability={r["sample"]:0 for r in unknown}
    eps_grid=[0.001,0.01,0.05]
    eps_preds=[]
    for eps in eps_grid:
        m=fit_classifier(clr(close_composition(x,eps)),y); eps_preds.append(m.predict(clr(close_composition(ux,eps))))
    for _ in range(perturbations):
        noise=rng.normal(0,.03,size=ux.shape); pert=close_composition(ux*np.exp(noise)); pp=model.predict(clr(pert));
        for r,p,base in zip(unknown,pp,upred): stability[r["sample"]]+=int(p==base)
    predictions={}
    for i,r in enumerate(unknown): predictions[r["sample"]]={"predicted_type":"铅钡" if upred[i] else "高钾","probability_lead_barium":float(up[i]),"perturbation_stability":float(stability[r["sample"]]/max(perturbations,1)),"zero_replacement_agreement":float(np.mean([p[i]==upred[i] for p in eps_preds]))}
    # permutation falsification: shuffle labels at artifact level
    actual=float(balanced_accuracy_score(y,cv_pred)); perm_scores=[]; unique_groups=np.unique(groups); group_label={g:int(y[np.where(groups==g)[0][0]]) for g in unique_groups}
    for _ in range(permutations):
        shuffled=rng.permutation([group_label[g] for g in unique_groups]); mapping=dict(zip(unique_groups,shuffled)); py=np.array([mapping[g] for g in groups])
        try: pp,_=loao_predictions(z,py,groups); perm_scores.append(float(balanced_accuracy_score(py,pp)))
        except ValueError: continue
    perm_p=float((1+sum(s>=actual for s in perm_scores))/(1+len(perm_scores)))
    # q4 bootstrap top correlation differences
    corr_by={};
    for typ in ("高钾","铅钡"):
        zz=z[np.array([r["type"]==typ for r in valid])]; corr_by[typ]=np.corrcoef(zz,rowvar=False)
    delta=corr_by["铅钡"]-corr_by["高钾"]; pairs=[]
    for i in range(14):
        for j in range(i+1,14): pairs.append({"pair":[OXIDES[i],OXIDES[j]],"delta_r":float(delta[i,j]),"abs_delta_r":float(abs(delta[i,j]))})
    pairs=sorted(pairs,key=lambda d:d["abs_delta_r"],reverse=True)[:10]
    metrics={
      "case_id":case["case_id"],"seed":SEED,
      "input_audit":{"known_rows":len(known),"valid_known_rows":len(valid),"invalid_known_rows":len(invalid),"invalid_samples":[r["sample"] for r in invalid],"artifact_rows":len(meta),"unknown_rows":len(unknown),"blank_interpretation":"not detected -> 0 before multiplicative replacement","valid_sum_interval":[85,105]},
      "q1_weathering":{"categorical_associations":categorical,"reconstruction_method":"type-specific unweathered CLR center; back-transform to closed composition","reconstruction_type_means":reconstruction},
      "q2_classification":{"baseline_rule":"PbO+BaO > K2O","baseline_accuracy":float(accuracy_score(y,baseline)),"loao_accuracy":float(accuracy_score(y,cv_pred)),"loao_balanced_accuracy":actual,"confusion_matrix_rows_true_0_highK_1_leadBarium":cm,"subtypes":subtype_metrics},
      "q3_unknown_classification":{"predictions":predictions},
      "q4_association":{"method":"Pearson correlation in CLR coordinates, descriptive because closure induces dependence","top_absolute_correlation_differences":pairs},
      "validation":{"split":"leave-one-artifact-out; all repeated sample points remain in the same fold","permutation_iterations_completed":len(perm_scores),"permutation_p":perm_p},
      "limitations":["Only audited rows_data were used; binary attachments were not opened.","Weathering reconstruction is a type-level CLR center, not a paired causal restoration for each artifact.","Subtypes are exploratory with small artifact counts.","Compositional correlations remain basis-dependent and are descriptive."],
    }
    fig_count=generate_figures(artifact_rows,valid,z,y,cv_prob,subtype,unknown,up,metrics,fig_dir)
    report={
      "problem_framing":{"questions":["weathering relations and pre-weathering composition","main-class rules and subtypes","unknown classification","within-class associations"],"unit_of_analysis":"artifact for categorical Q1; valid sampling point for chemistry, grouped by artifact during validation"},
      "data_audit":metrics["input_audit"],
      "assumptions":["Blank chemical cells mean not detected and are treated as structural zeros before small positive replacement.","Rows with measured sums in the inclusive 85–105 interval are valid.","Explicit sampling-point labels override artifact-level surface weathering.","Audited rows_data is the complete available benchmark input."],
      "candidate_models":{"selected":"CLR logistic regression with artifact-grouped validation; Ward clustering within class; CLR correlations","alternatives":["raw-percentage LDA as a non-compositional comparator","tree classifier, rejected as less stable for this small sample"]},
      "baseline":metrics["q2_classification"],
      "math_specification":{"closure":"c_i=(x_i+delta I[x_i=0])/sum_j(...) ","clr":"z_i=log(c_i)-mean_j log(c_j)","classifier":"P(y=1|z)=sigmoid(beta0+beta^T standardized(z))","reconstruction":"inverse-clr of the unweathered class CLR center"},
      "code_prototype":{"entrypoint":"analysis.py","outputs":["results/metrics.json","results/modeling_report.json","results/predictions.csv","figures/*.png","figures/*.svg"]},
      "experiment":{"seed":SEED,"zero_replacements":eps_grid,"perturbation_sigma_log":0.03,"perturbations":perturbations},
      "validation":metrics["validation"],
      "sensitivity_robustness":{"unknown_perturbations":predictions,"zero_replacement_grid":eps_grid},
      "falsification":{"label_permutation_null":"artifact labels permuted then full LOAO repeated","observed_balanced_accuracy":actual,"p_value":perm_p},
      "reviewer_risks":metrics["limitations"],
      "reproducibility_manifest":{"command":f'python analysis.py --input "{input_path}" --output .',"input_sha256":hashlib.sha256(input_path.read_bytes()).hexdigest(),"declared_problem_sha256":case["problem_sha256"],"declared_data_sha256":case["data_sha256"],"python":sys.version.split()[0],"platform":platform.platform(),"seed":SEED,"runtime_seconds":None},
    }
    with (result_dir/"predictions.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.writer(f); w.writerow(["sample","predicted_type","probability_lead_barium","perturbation_stability","zero_replacement_agreement"])
        for n,d in predictions.items(): w.writerow([n,d["predicted_type"],d["probability_lead_barium"],d["perturbation_stability"],d["zero_replacement_agreement"]])
    runtime=time.time()-started; report["reproducibility_manifest"]["runtime_seconds"]=runtime; metrics["runtime_seconds"]=runtime
    (result_dir/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
    (result_dir/"modeling_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (result_dir/"reproducibility_manifest.json").write_text(json.dumps(report["reproducibility_manifest"],ensure_ascii=False,indent=2),encoding="utf-8")
    return {"figures_count":fig_count,"metrics":metrics}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--input",default=DEFAULT_INPUT); parser.add_argument("--output",default="."); parser.add_argument("--permutations",type=int,default=499); parser.add_argument("--perturbations",type=int,default=499); args=parser.parse_args()
    receipt=run(Path(args.input),Path(args.output),args.permutations,args.perturbations); print(json.dumps({"status":"completed","figures_count":receipt["figures_count"]},ensure_ascii=False))


if __name__ == "__main__": main()

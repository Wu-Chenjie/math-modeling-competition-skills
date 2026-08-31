#!/usr/bin/env python3
"""Deterministic analysis for CUMCM 2022 C using only audited JSON rows."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy.stats import chi2_contingency


SEED = 20220915
TYPE_K = "high-potassium"
TYPE_LB = "lead-barium"
WEATHERED = "weathered"
UNWEATHERED = "unweathered"


def _default_case_json() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if parent.name == "math-modeling-competition-skills":
            return parent / "benchmarks" / "case-summaries" / "cumcm-2022-c.json"
    raise FileNotFoundError("math-modeling-competition-skills root not found")


CASE_JSON = _default_case_json()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _number(value: object) -> float:
    return 0.0 if value in (None, "") else float(value)


def load_case(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    sheets = raw["data_audit"][0]["sheets"]
    s1, s2, s3 = (s["rows_data"] for s in sheets)
    meta = []
    for row in s1[1:]:
        meta.append(
            {
                "artifact": str(row[0]).zfill(2),
                "decoration": str(row[1]),
                "type": TYPE_K if row[2] == "\u9ad8\u94be" else TYPE_LB,
                "color": str(row[3]) if row[3] else "missing",
                "state": WEATHERED if row[4] == "\u98ce\u5316" else UNWEATHERED,
            }
        )
    meta_by_id = {r["artifact"]: r for r in meta}
    components = []
    for header in s2[0][1:]:
        match = re.search(r"\(([^)]+)\)", header)
        components.append(match.group(1) if match else header)
    chem = []
    for row in s2[1:]:
        sample = str(row[0])
        artifact = re.match(r"\d+", sample).group(0).zfill(2)
        values = np.array([_number(v) for v in row[1:]], dtype=float)
        if "\u672a\u98ce\u5316\u70b9" in sample:
            state = UNWEATHERED
        elif "\u4e25\u91cd\u98ce\u5316\u70b9" in sample:
            state = WEATHERED
        else:
            state = meta_by_id[artifact]["state"]
        total = float(values.sum())
        chem.append(
            {
                "sample": sample,
                "artifact": artifact,
                "type": meta_by_id[artifact]["type"],
                "state": state,
                "values": values,
                "total": total,
                "valid": 85.0 <= total <= 105.0,
            }
        )
    unknown = []
    for row in s3[1:]:
        values = np.array([_number(v) for v in row[2:]], dtype=float)
        total = float(values.sum())
        unknown.append(
            {
                "artifact": str(row[0]),
                "state": WEATHERED if row[1] == "\u98ce\u5316" else UNWEATHERED,
                "values": values,
                "total": total,
                "valid": 85.0 <= total <= 105.0,
            }
        )
    return {
        "meta": meta,
        "chem": chem,
        "unknown": unknown,
        "components": components,
        "source": raw,
    }


def close_composition(x: np.ndarray) -> np.ndarray:
    x = np.atleast_2d(np.asarray(x, dtype=float))
    return x / x.sum(axis=1, keepdims=True) * 100.0


def replace_zeros(x: np.ndarray, delta: float = 0.1) -> np.ndarray:
    x = close_composition(x)
    out = x.copy()
    for i, row in enumerate(out):
        zero = row <= 0
        z = int(zero.sum())
        if z:
            positive_total = row[~zero].sum()
            row[~zero] *= (100.0 - z * delta) / positive_total
            row[zero] = delta
            out[i] = row
    return out


def clr(x: np.ndarray, delta: float = 0.1) -> np.ndarray:
    logged = np.log(replace_zeros(x, delta))
    return logged - logged.mean(axis=1, keepdims=True)


def nearest_centroid(x: np.ndarray, labels: list[str], centroids: np.ndarray):
    d = np.linalg.norm(np.asarray(x)[:, None, :] - centroids[None, :, :], axis=2)
    order = np.argsort(d, axis=1)
    pred = [labels[i] for i in order[:, 0]]
    margin = d[np.arange(len(d)), order[:, 1]] - d[np.arange(len(d)), order[:, 0]]
    return pred, margin


def aggregate_artifacts(rows: list[dict], delta: float = 0.1):
    grouped = defaultdict(list)
    labels = {}
    for row in rows:
        if row["valid"]:
            grouped[row["artifact"]].append(replace_zeros(row["values"], delta)[0])
            labels[row["artifact"]] = row["type"]
    ids = sorted(grouped)
    x = np.vstack([close_composition(np.mean(grouped[i], axis=0))[0] for i in ids])
    y = np.array([labels[i] for i in ids])
    return ids, x, y


def fit_rlda(x: np.ndarray, y: np.ndarray, alpha: float = 0.2):
    labels = sorted(set(y))
    means = np.vstack([x[y == label].mean(axis=0) for label in labels])
    centered = np.vstack([x[y == label] - means[i] for i, label in enumerate(labels)])
    cov = centered.T @ centered / max(len(x) - len(labels), 1)
    scale = np.trace(cov) / cov.shape[0]
    cov = (1.0 - alpha) * cov + alpha * scale * np.eye(cov.shape[0])
    inv = np.linalg.pinv(cov)
    priors = np.array([(y == label).mean() for label in labels])
    return labels, means, inv, priors


def predict_rlda(model, x: np.ndarray):
    labels, means, inv, priors = model
    scores = np.column_stack(
        [x @ inv @ mean - 0.5 * mean @ inv @ mean + math.log(prior) for mean, prior in zip(means, priors)]
    )
    order = np.argsort(scores, axis=1)
    pred = np.array([labels[i] for i in order[:, -1]])
    margin = scores[np.arange(len(x)), order[:, -1]] - scores[np.arange(len(x)), order[:, -2]]
    return pred, margin, scores


def classification_experiment(x: np.ndarray, y: np.ndarray, delta: float = 0.1, alpha: float = 0.2):
    z = clr(x, delta)
    pred = []
    margin = []
    for i in range(len(z)):
        mask = np.arange(len(z)) != i
        p, m, _ = predict_rlda(fit_rlda(z[mask], y[mask], alpha), z[i : i + 1])
        pred.append(p[0])
        margin.append(float(m[0]))
    pred = np.array(pred)
    labels = [TYPE_K, TYPE_LB]
    cm = [[int(np.sum((y == a) & (pred == b))) for b in labels] for a in labels]
    return {
        "accuracy": float(np.mean(pred == y)),
        "balanced_accuracy": float(np.mean([np.mean(pred[y == label] == label) for label in labels])),
        "confusion": cm,
        "pred": pred,
        "margin": np.array(margin),
    }


def cramers_v(table: np.ndarray) -> float:
    chi2 = chi2_contingency(table, correction=False)[0]
    n = table.sum()
    return float(math.sqrt(chi2 / (n * max(1, min(table.shape) - 1))))


def association_test(meta: list[dict], field: str, rng: np.random.Generator, permutations: int = 5000):
    rows = [r for r in meta if r[field] != "missing"]
    cats = sorted({r[field] for r in rows})
    state = np.array([r["state"] == WEATHERED for r in rows])
    group = np.array([cats.index(r[field]) for r in rows])

    def table_for(s):
        return np.array([[np.sum((group == j) & (s == k)) for k in (False, True)] for j in range(len(cats))])

    table = table_for(state)
    observed = chi2_contingency(table, correction=False)[0]
    exceed = sum(chi2_contingency(table_for(rng.permutation(state)), correction=False)[0] >= observed - 1e-12 for _ in range(permutations))
    return {
        "categories": cats,
        "table_unweathered_weathered": table.tolist(),
        "cramers_v": cramers_v(table),
        "permutation_p": (exceed + 1) / (permutations + 1),
        "n": len(rows),
    }


def state_artifact_means(rows: list[dict], delta: float = 0.1):
    grouped = defaultdict(list)
    for r in rows:
        if r["valid"]:
            grouped[(r["artifact"], r["type"], r["state"])].append(replace_zeros(r["values"], delta)[0])
    result = []
    for (artifact, glass_type, state), values in sorted(grouped.items()):
        result.append(
            {"artifact": artifact, "type": glass_type, "state": state, "values": close_composition(np.mean(values, axis=0))[0]}
        )
    return result


def inverse_clr(z: np.ndarray) -> np.ndarray:
    z = np.asarray(z)
    e = np.exp(z - np.max(z))
    return e / e.sum() * 100.0


def restoration_analysis(rows: list[dict], components: list[str], delta: float = 0.1):
    means = state_artifact_means(rows, delta)
    shifts = {}
    changes = {}
    for glass_type in (TYPE_K, TYPE_LB):
        w = np.vstack([r["values"] for r in means if r["type"] == glass_type and r["state"] == WEATHERED])
        u = np.vstack([r["values"] for r in means if r["type"] == glass_type and r["state"] == UNWEATHERED])
        shifts[glass_type] = clr(w, delta).mean(axis=0) - clr(u, delta).mean(axis=0)
        raw_diff = w.mean(axis=0) - u.mean(axis=0)
        idx = np.argsort(np.abs(raw_diff))[::-1][:5]
        changes[glass_type] = [
            {"component": components[i], "weathered_minus_unweathered_pp": float(raw_diff[i])} for i in idx
        ]
    by_key = {(r["artifact"], r["state"]): r for r in means}
    paired = sorted({r["artifact"] for r in means if (r["artifact"], WEATHERED) in by_key and (r["artifact"], UNWEATHERED) in by_key})
    validations = []
    for artifact in paired:
        w = by_key[(artifact, WEATHERED)]
        target = by_key[(artifact, UNWEATHERED)]["values"]
        train = [r for r in means if r["type"] == w["type"] and r["artifact"] != artifact]
        tw = np.vstack([r["values"] for r in train if r["state"] == WEATHERED])
        tu = np.vstack([r["values"] for r in train if r["state"] == UNWEATHERED])
        shift = clr(tw, delta).mean(axis=0) - clr(tu, delta).mean(axis=0)
        prediction = inverse_clr(clr(w["values"], delta)[0] - shift)
        rmse = float(np.sqrt(np.mean((prediction - target) ** 2)))
        ait = float(np.linalg.norm(clr(prediction, delta)[0] - clr(target, delta)[0]))
        validations.append({"artifact": artifact, "type": w["type"], "prediction": prediction, "target": target, "rmse_pp": rmse, "aitchison_distance": ait})
    predictions = []
    for r in means:
        if r["state"] == WEATHERED:
            pred = inverse_clr(clr(r["values"], delta)[0] - shifts[r["type"]])
            predictions.append({"artifact": r["artifact"], "type": r["type"], "prediction": pred})
    metrics = {
        "paired_artifacts": len(validations),
        "loao_rmse_pp_mean": float(np.mean([v["rmse_pp"] for v in validations])) if validations else None,
        "loao_rmse_pp_median": float(np.median([v["rmse_pp"] for v in validations])) if validations else None,
        "loao_aitchison_mean": float(np.mean([v["aitchison_distance"] for v in validations])) if validations else None,
        "top_weathering_changes": changes,
    }
    return metrics, validations, predictions, shifts


def pca2(z: np.ndarray):
    centered = z - z.mean(axis=0)
    _, s, vt = np.linalg.svd(centered, full_matrices=False)
    scores = centered @ vt[:2].T
    explained = (s[:2] ** 2) / np.sum(s**2)
    return scores, explained


def kmeans(x: np.ndarray, k: int, rng: np.random.Generator, restarts: int = 50):
    best = None
    for _ in range(restarts):
        centers = x[rng.choice(len(x), k, replace=False)].copy()
        labels = np.zeros(len(x), dtype=int)
        for _ in range(100):
            new_labels = np.argmin(np.linalg.norm(x[:, None, :] - centers[None, :, :], axis=2), axis=1)
            if np.array_equal(labels, new_labels) and _ > 0:
                break
            labels = new_labels
            for j in range(k):
                if np.any(labels == j):
                    centers[j] = x[labels == j].mean(axis=0)
        inertia = float(np.sum((x - centers[labels]) ** 2))
        if best is None or inertia < best[0]:
            best = (inertia, labels.copy(), centers.copy())
    return best[1], best[2], best[0]


def silhouette(x: np.ndarray, labels: np.ndarray) -> float:
    d = np.linalg.norm(x[:, None, :] - x[None, :, :], axis=2)
    scores = []
    for i in range(len(x)):
        same = labels == labels[i]
        a = d[i, same].sum() / max(same.sum() - 1, 1)
        b = min(d[i, labels == lab].mean() for lab in set(labels) if lab != labels[i])
        scores.append((b - a) / max(a, b, 1e-12))
    return float(np.mean(scores))


def adjusted_rand(a: np.ndarray, b: np.ndarray) -> float:
    contingency = np.zeros((len(set(a)), len(set(b))), dtype=int)
    for x, y in zip(a, b):
        contingency[x, y] += 1
    comb2 = lambda n: n * (n - 1) / 2
    sum_cells = sum(comb2(v) for v in contingency.ravel())
    sum_a = sum(comb2(v) for v in contingency.sum(axis=1))
    sum_b = sum(comb2(v) for v in contingency.sum(axis=0))
    total = comb2(len(a))
    expected = sum_a * sum_b / total if total else 0
    maximum = 0.5 * (sum_a + sum_b)
    return float((sum_cells - expected) / (maximum - expected)) if maximum != expected else 1.0


def subclass_analysis(ids, x, y, components, seed=SEED):
    output = {}
    assignments = []
    for type_index, glass_type in enumerate((TYPE_K, TYPE_LB)):
        mask = y == glass_type
        ids_t = np.array(ids)[mask]
        x_t = x[mask]
        z = clr(x_t, 0.1)
        candidates = []
        for k in range(2, min(4, len(z) - 1) + 1):
            labels, _, inertia = kmeans(z, k, np.random.default_rng(seed + type_index * 100 + k))
            sizes = Counter(labels)
            score = silhouette(z, labels) if min(sizes.values()) >= 3 else -1.0
            candidates.append((score, k, labels, inertia))
        score, k, labels, inertia = max(candidates, key=lambda v: v[0])
        cluster_means = np.vstack([x_t[labels == j].mean(axis=0) for j in range(k)])
        separation = np.ptp(cluster_means, axis=0)
        selected = [components[i] for i in np.argsort(separation)[::-1][:4]]
        aris = []
        for dindex, delta in enumerate((0.05, 0.1, 0.2, 0.5)):
            zz = clr(x_t, delta)
            lab, _, _ = kmeans(zz, k, np.random.default_rng(seed + 900 + type_index * 10 + dindex))
            aris.append(adjusted_rand(labels, lab))
        output[glass_type] = {
            "k": k,
            "silhouette": score,
            "cluster_sizes": dict(Counter(map(int, labels))),
            "selected_components": selected,
            "zero_replacement_ari_min": float(min(aris)),
            "candidate_silhouettes": {str(v[1]): float(v[0]) for v in candidates},
        }
        for artifact, label in zip(ids_t, labels):
            assignments.append({"artifact": artifact, "type": glass_type, "subclass": int(label) + 1})
    return output, assignments


def proportionality(x: np.ndarray, delta: float = 0.1):
    logx = np.log(replace_zeros(x, delta))
    d = x.shape[1]
    rho = np.eye(d)
    for i in range(d):
        for j in range(i + 1, d):
            denom = np.var(logx[:, i], ddof=1) + np.var(logx[:, j], ddof=1)
            value = 1.0 - np.var(logx[:, i] - logx[:, j], ddof=1) / denom if denom else 0.0
            rho[i, j] = rho[j, i] = value
    return rho


def association_difference(x, y, components, rng, permutations=2000):
    rk = proportionality(x[y == TYPE_K])
    rlb = proportionality(x[y == TYPE_LB])
    iu = np.triu_indices(x.shape[1], 1)
    diff = np.abs(rk - rlb)
    observed_max = float(diff[iu].max())
    exceed = 0
    for _ in range(permutations):
        yp = rng.permutation(y)
        pd = np.abs(proportionality(x[yp == TYPE_K]) - proportionality(x[yp == TYPE_LB]))
        exceed += pd[iu].max() >= observed_max - 1e-12
    order = np.argsort(diff[iu])[::-1][:8]
    top_diff = []
    for index in order:
        i, j = iu[0][index], iu[1][index]
        top_diff.append({"pair": f"{components[i]}/{components[j]}", TYPE_K: float(rk[i, j]), TYPE_LB: float(rlb[i, j]), "absolute_difference": float(diff[i, j])})
    def top_positive(r):
        order_r = np.argsort(r[iu])[::-1][:5]
        return [{"pair": f"{components[iu[0][q]]}/{components[iu[1][q]]}", "rho": float(r[iu[0][q], iu[1][q]])} for q in order_r]
    return {
        "rho": {TYPE_K: rk, TYPE_LB: rlb},
        "top_positive": {TYPE_K: top_positive(rk), TYPE_LB: top_positive(rlb)},
        "top_differences": top_diff,
        "global_max_difference_permutation_p": (exceed + 1) / (permutations + 1),
    }


def save_figure(fig, base: Path):
    fig.savefig(base.with_suffix(".png"), dpi=300, bbox_inches="tight", metadata={"Software": "math_model_run.py"})
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)


def make_figures(figdir, meta, components, ids, x, y, cls, subclasses, unknown_x, unknown_pred, unknown_margin, unknown_agreement, restoration, assoc):
    plt.rcParams.update({"font.size": 8, "svg.hashsalt": "cumcm-2022-c", "axes.spines.top": False, "axes.spines.right": False})
    colors = {TYPE_K: "#0072B2", TYPE_LB: "#D55E00"}
    figdir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(5.8, 3.4))
    labels = ["type", "decoration", "color"]
    rates = []
    names = []
    for field in labels:
        for cat in sorted({r[field] for r in meta if r[field] != "missing"}):
            rr = [r for r in meta if r[field] == cat]
            rates.append(sum(r["state"] == WEATHERED for r in rr) / len(rr))
            names.append(f"{field}:{cat}")
    ax.barh(range(len(rates)), rates, color="#56B4E9")
    ax.set(yticks=range(len(rates)), yticklabels=names, xlim=(0, 1), xlabel="Weathered fraction")
    save_figure(fig, figdir / "raw_q1_metadata_weathering")

    fig, ax = plt.subplots(figsize=(5.8, 3.2))
    for offset, glass_type in enumerate((TYPE_K, TYPE_LB)):
        changes = restoration["metrics"]["top_weathering_changes"][glass_type]
        ax.scatter([c["weathered_minus_unweathered_pp"] for c in changes], np.arange(5) + offset * 0.12, label=glass_type, color=colors[glass_type])
    ax.axvline(0, color="black", lw=0.7)
    ax.set(yticks=np.arange(5), yticklabels=[c["component"] for c in restoration["metrics"]["top_weathering_changes"][TYPE_K]], xlabel="Weathered - unweathered (percentage points)")
    ax.legend(frameon=False)
    save_figure(fig, figdir / "process_q1_weathering_shifts")

    fig, ax = plt.subplots(figsize=(4, 4))
    for v in restoration["validations"]:
        ax.scatter(v["target"], v["prediction"], s=13, alpha=0.65, color=colors[v["type"]])
    ax.plot([0, 100], [0, 100], "k--", lw=0.8)
    ax.set(xlabel="Observed unweathered (%)", ylabel="Restored prediction (%)", xlim=(0, 100), ylim=(0, 100))
    save_figure(fig, figdir / "result_q1_restoration_validation")

    z = clr(x)
    score, exp = pca2(z)
    fig, ax = plt.subplots(figsize=(4.8, 3.7))
    for glass_type in (TYPE_K, TYPE_LB):
        m = y == glass_type
        ax.scatter(score[m, 0], score[m, 1], label=glass_type, color=colors[glass_type], edgecolor="white", linewidth=0.3)
    ax.set(xlabel=f"PC1 ({exp[0]*100:.1f}%)", ylabel=f"PC2 ({exp[1]*100:.1f}%)")
    ax.legend(frameon=False)
    save_figure(fig, figdir / "raw_q2_clr_pca")

    fig, ax = plt.subplots(figsize=(3.7, 3.4))
    im = ax.imshow(np.array(cls["confusion"]), cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, cls["confusion"][i][j], ha="center", va="center")
    ax.set(xticks=[0, 1], yticks=[0, 1], xticklabels=["K", "PbBa"], yticklabels=["K", "PbBa"], xlabel="Predicted", ylabel="Observed")
    fig.colorbar(im, ax=ax, shrink=0.7)
    save_figure(fig, figdir / "process_q2_loao_confusion")

    submap = {a["artifact"]: a["subclass"] for a in subclasses}
    fig, ax = plt.subplots(figsize=(4.8, 3.7))
    markers = {1: "o", 2: "s", 3: "^", 4: "D"}
    for i, artifact in enumerate(ids):
        ax.scatter(score[i, 0], score[i, 1], marker=markers[submap[artifact]], color=colors[y[i]], s=30)
    ax.set(xlabel="CLR-PC1", ylabel="CLR-PC2")
    save_figure(fig, figdir / "result_q2_subclasses")

    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    im = ax.imshow(close_composition(unknown_x), aspect="auto", cmap="viridis")
    ax.set(yticks=range(len(unknown_x)), yticklabels=[f"A{i}" for i in range(1, 9)], xticks=range(len(components)), xticklabels=components)
    ax.tick_params(axis="x", rotation=45)
    fig.colorbar(im, ax=ax, label="Normalized %", shrink=0.75)
    save_figure(fig, figdir / "raw_q3_unknown_composition")

    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    ax.bar(range(8), unknown_agreement, color=[colors[p] for p in unknown_pred])
    ax.set(xticks=range(8), xticklabels=[f"A{i}" for i in range(1, 9)], ylim=(0, 1.05), ylabel="Agreement across settings")
    save_figure(fig, figdir / "process_q3_sensitivity")

    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    ax.barh(range(8), unknown_margin, color=[colors[p] for p in unknown_pred])
    ax.set(yticks=range(8), yticklabels=[f"A{i}" for i in range(1, 9)], xlabel="RLDA score margin")
    save_figure(fig, figdir / "result_q3_classification_margin")

    fig, ax = plt.subplots(figsize=(4.4, 3.8))
    corr = np.corrcoef(z, rowvar=False)
    im = ax.imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set(xticks=range(len(components)), yticks=range(len(components)), xticklabels=components, yticklabels=components)
    ax.tick_params(axis="x", rotation=45)
    fig.colorbar(im, ax=ax, shrink=0.72)
    save_figure(fig, figdir / "raw_q4_pooled_clr_correlation")

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharex=True, sharey=True)
    for ax, glass_type in zip(axes, (TYPE_K, TYPE_LB)):
        im = ax.imshow(assoc["rho"][glass_type], vmin=-1, vmax=1, cmap="RdBu_r")
        ax.set_title(glass_type)
        ax.set(xticks=range(len(components)), yticks=range(len(components)), xticklabels=components, yticklabels=components)
        ax.tick_params(axis="x", rotation=45)
    fig.colorbar(im, ax=axes, shrink=0.75, label="Proportionality rho")
    save_figure(fig, figdir / "process_q4_type_proportionality")

    top = assoc["top_differences"]
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    yy = np.arange(len(top))
    for i, item in enumerate(top):
        ax.plot([item[TYPE_K], item[TYPE_LB]], [i, i], color="#999999", lw=1)
    ax.scatter([t[TYPE_K] for t in top], yy, color=colors[TYPE_K], label=TYPE_K)
    ax.scatter([t[TYPE_LB] for t in top], yy, color=colors[TYPE_LB], label=TYPE_LB)
    ax.set(yticks=yy, yticklabels=[t["pair"] for t in top], xlabel="Proportionality rho")
    ax.legend(frameon=False)
    save_figure(fig, figdir / "result_q4_association_differences")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def json_ready(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, dict):
        return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_ready(v) for v in value]
    return value


def run(input_path: Path, out_root: Path):
    started = time.perf_counter()
    rng = np.random.default_rng(SEED)
    data = load_case(input_path)
    results = out_root / "results"
    figures = out_root / "figures"
    results.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    valid = [r for r in data["chem"] if r["valid"]]
    ids, x, y = aggregate_artifacts(data["chem"])

    q1_assoc = {field: association_test(data["meta"], field, rng) for field in ("type", "decoration", "color")}
    rest_metrics, validations, restored, shifts = restoration_analysis(data["chem"], data["components"])
    restoration = {"metrics": rest_metrics, "validations": validations, "predictions": restored, "shifts": shifts}

    cls = classification_experiment(x, y)
    majority = float(max(Counter(y).values()) / len(y))
    k_index, pb_index, ba_index = data["components"].index("K2O"), data["components"].index("PbO"), data["components"].index("BaO")
    rule_pred = np.where(x[:, pb_index] + x[:, ba_index] > x[:, k_index], TYPE_LB, TYPE_K)
    rule_accuracy = float(np.mean(rule_pred == y))
    sub_metrics, subclasses = subclass_analysis(ids, x, y, data["components"])

    ux = np.vstack([r["values"] for r in data["unknown"] if r["valid"]])
    full_model = fit_rlda(clr(x), y)
    unknown_pred, unknown_margin, _ = predict_rlda(full_model, clr(ux))
    settings = []
    for delta in (0.05, 0.1, 0.2, 0.5):
        for alpha in (0.05, 0.2, 0.5):
            p, _, _ = predict_rlda(fit_rlda(clr(x, delta), y, alpha), clr(ux, delta))
            settings.append(p)
    settings = np.vstack(settings)
    agreement = np.mean(settings == unknown_pred[None, :], axis=0)
    unknown_rows = [
        {"artifact": r["artifact"], "prediction": p, "rlda_margin": float(m), "sensitivity_agreement": float(a), "composition_total": r["total"]}
        for r, p, m, a in zip([r for r in data["unknown"] if r["valid"]], unknown_pred, unknown_margin, agreement)
    ]

    assoc = association_difference(x, y, data["components"], rng)
    metrics = {
        "case_id": data["source"]["case_id"],
        "data_audit": {
            "metadata_artifacts": len(data["meta"]),
            "classified_samples": len(data["chem"]),
            "valid_classified_samples": len(valid),
            "invalid_sample_ids": [r["sample"] for r in data["chem"] if not r["valid"]],
            "valid_artifacts_for_modeling": len(ids),
            "unknown_samples": len(data["unknown"]),
            "valid_unknown_samples": int(sum(r["valid"] for r in data["unknown"])),
            "composition_total_range_classified": [float(min(r["total"] for r in data["chem"])), float(max(r["total"] for r in data["chem"]))],
        },
        "q1": {"categorical_associations": q1_assoc, "restoration": rest_metrics},
        "q2": {
            "majority_baseline_accuracy": majority,
            "chemical_rule_accuracy": rule_accuracy,
            "rlda_loao_accuracy": cls["accuracy"],
            "rlda_loao_balanced_accuracy": cls["balanced_accuracy"],
            "rlda_confusion_order_K_PbBa": cls["confusion"],
            "subclasses": sub_metrics,
        },
        "q3": {"predictions": unknown_rows},
        "q4": {
            "top_positive": assoc["top_positive"],
            "top_differences": assoc["top_differences"],
            "global_max_difference_permutation_p": assoc["global_max_difference_permutation_p"],
        },
        "parameters": {"seed": SEED, "valid_total_interval": [85, 105], "zero_replacement_percent": 0.1, "rlda_shrinkage": 0.2, "permutations_q1": 5000, "permutations_q4": 2000},
    }
    (results / "metrics.json").write_text(json.dumps(json_ready(metrics), ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(results / "unknown_predictions.csv", list(unknown_rows[0]), unknown_rows)
    write_csv(results / "subclass_assignments.csv", ["artifact", "type", "subclass"], subclasses)
    restoration_rows = []
    for r in restored:
        row = {"artifact": r["artifact"], "type": r["type"]}
        row.update({f"predicted_{c}": float(v) for c, v in zip(data["components"], r["prediction"])})
        restoration_rows.append(row)
    write_csv(results / "restored_unweathered_compositions.csv", list(restoration_rows[0]), restoration_rows)
    make_figures(figures, data["meta"], data["components"], ids, x, y, cls, subclasses, ux, unknown_pred, unknown_margin, agreement, restoration, assoc)

    artifacts = sorted([p for p in results.glob("*") if p.name != "reproducibility_manifest.json"] + list(figures.glob("*")))
    manifest = {
        "case_id": data["source"]["case_id"],
        "seed": SEED,
        "input": {"path": str(input_path), "sha256": sha256(input_path), "problem_sha256_recorded": data["source"]["problem_sha256"], "data_sha256_recorded": data["source"]["data_sha256"]},
        "script": {"path": str(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
        "command": "python math_model_run.py",
        "runtime_seconds": round(time.perf_counter() - started, 6),
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "matplotlib": matplotlib.__version__},
        "artifacts": [{"path": str(p.relative_to(out_root)), "sha256": sha256(p)} for p in artifacts],
    }
    (results / "reproducibility_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "metrics": str(results / "metrics.json"), "figures": len(list(figures.glob("*.png"))), "valid_samples": len(valid)}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=CASE_JSON)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    run(args.input.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()

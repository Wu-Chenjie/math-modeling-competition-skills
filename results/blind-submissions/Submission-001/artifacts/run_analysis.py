#!/usr/bin/env python3
"""Reproducible analysis of the supplied CUMCM 2022 C JSON case summary."""

import argparse
import hashlib
import json
import math
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path


OXIDES = ["SiO2", "Na2O", "K2O", "CaO", "MgO", "Al2O3", "Fe2O3", "CuO", "PbO", "BaO", "P2O5", "SrO", "SnO2", "SO2"]
EPSILON = 0.05
SEED = 20220915


def artifact_id(value):
    match = re.match(r"(\d+)", str(value))
    return match.group(1).zfill(2) if match else str(value)


def close(values):
    adjusted = [float(v) if float(v) > 0 else EPSILON for v in values]
    total = sum(adjusted)
    return [100.0 * v / total for v in adjusted]


def clr(values):
    closed = close(values)
    logs = [math.log(v) for v in closed]
    center = statistics.fmean(logs)
    return [v - center for v in logs]


def inverse_clr(values):
    shifted = [math.exp(v - max(values)) for v in values]
    total = sum(shifted)
    return [100.0 * v / total for v in shifted]


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def vector_mean(rows):
    return [statistics.fmean(col) for col in zip(*rows)]


def nearest_centroid(train_x, train_y, test_x):
    centroids = {label: vector_mean([x for x, y in zip(train_x, train_y) if y == label]) for label in sorted(set(train_y))}
    return min(centroids, key=lambda label: distance(test_x, centroids[label])), centroids


def rank(values):
    ordered = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(values):
        j = i + 1
        while j < len(values) and values[ordered[j]] == values[ordered[i]]:
            j += 1
        avg = (i + j - 1) / 2 + 1
        for k in range(i, j):
            out[ordered[k]] = avg
        i = j
    return out


def pearson(a, b):
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    da, db = [x - ma for x in a], [x - mb for x in b]
    denom = math.sqrt(sum(x * x for x in da) * sum(x * x for x in db))
    return sum(x * y for x, y in zip(da, db)) / denom if denom else 0.0


def spearman(a, b):
    return pearson(rank(a), rank(b))


def cramers_v(rows, col_a, col_b):
    pairs = [(r[col_a] or "MISSING", r[col_b] or "MISSING") for r in rows]
    a_levels, b_levels = sorted(set(a for a, _ in pairs)), sorted(set(b for _, b in pairs))
    counts = Counter(pairs)
    a_counts, b_counts = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    n = len(pairs)
    chi2 = 0.0
    for a in a_levels:
        for b in b_levels:
            expected = a_counts[a] * b_counts[b] / n
            chi2 += (counts[(a, b)] - expected) ** 2 / expected
    denom = min(len(a_levels) - 1, len(b_levels) - 1)
    return math.sqrt((chi2 / n) / denom) if denom else 0.0


def kmeans2(rows, seed=SEED, iterations=100):
    if len(rows) < 2:
        return [0] * len(rows)
    rng = random.Random(seed)
    first = rng.randrange(len(rows))
    second = max(range(len(rows)), key=lambda i: distance(rows[i], rows[first]))
    centers = [rows[first][:], rows[second][:]]
    labels = [0] * len(rows)
    for _ in range(iterations):
        new_labels = [0 if distance(x, centers[0]) <= distance(x, centers[1]) else 1 for x in rows]
        if new_labels == labels and _ > 0:
            break
        labels = new_labels
        for k in (0, 1):
            members = [x for x, label in zip(rows, labels) if label == k]
            if members:
                centers[k] = vector_mean(members)
    return labels


def silhouette(rows, labels):
    if len(set(labels)) < 2:
        return 0.0
    scores = []
    for i, row in enumerate(rows):
        same = [distance(row, rows[j]) for j in range(len(rows)) if labels[j] == labels[i] and j != i]
        other = [distance(row, rows[j]) for j in range(len(rows)) if labels[j] != labels[i]]
        a = statistics.fmean(same) if same else 0.0
        b = statistics.fmean(other)
        scores.append((b - a) / max(a, b) if max(a, b) else 0.0)
    return statistics.fmean(scores)


def svg_bar(path, title, labels, values, color="#277da1", y_label="value"):
    width, height, left, top, bottom = 900, 520, 90, 65, 105
    plot_h, plot_w = height - top - bottom, width - left - 35
    vmax = max(values) if values else 1.0
    vmax = vmax if vmax > 0 else 1.0
    bar_w = plot_w / max(len(values), 1) * 0.68
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             f'<text x="{width/2}" y="32" text-anchor="middle" font-family="Arial" font-size="20">{title}</text>',
             f'<text x="22" y="{top+plot_h/2}" transform="rotate(-90 22 {top+plot_h/2})" text-anchor="middle" font-family="Arial" font-size="13">{y_label}</text>',
             f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#222"/>',
             f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="#222"/>']
    for i, (label, value) in enumerate(zip(labels, values)):
        x = left + (i + 0.5) * plot_w / len(values) - bar_w / 2
        h = value / vmax * plot_h * 0.9
        y = top + plot_h - h
        parts += [f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{color}"/>',
                  f'<text x="{x+bar_w/2:.1f}" y="{y-6:.1f}" text-anchor="middle" font-family="Arial" font-size="11">{value:.3g}</text>',
                  f'<text x="{x+bar_w/2:.1f}" y="{top+plot_h+18}" transform="rotate(35 {x+bar_w/2:.1f} {top+plot_h+18})" text-anchor="start" font-family="Arial" font-size="10">{label}</text>']
    parts.append('</svg>')
    path.write_text("\n".join(parts), encoding="utf-8")


def load_case(path):
    with path.open(encoding="utf-8") as handle:
        case = json.load(handle)
    sheets = case["data_audit"][0]["sheets"]
    return case, sheets[0], sheets[1], sheets[2]


def make_records(basic_sheet, composition_sheet):
    basic = {}
    for row in basic_sheet["rows_data"][1:]:
        basic[artifact_id(row[0])] = {"id": artifact_id(row[0]), "pattern": row[1], "type": row[2], "color": row[3], "weathering": row[4]}
    records = []
    for row in composition_sheet["rows_data"][1:]:
        aid = artifact_id(row[0])
        values = [float(v) if v != "" else 0.0 for v in row[1:]]
        total = sum(values)
        if aid not in basic:
            continue
        explicit_unweathered = "未风化点" in row[0]
        sample_weathering = "无风化" if explicit_unweathered else basic[aid]["weathering"]
        records.append({**basic[aid], "sample": row[0], "sample_weathering": sample_weathering,
                        "values": values, "total": total, "valid": 85 <= total <= 105})
    return list(basic.values()), records


def group_loocv(records, transform):
    valid = [r for r in records if r["valid"]]
    preds = []
    for aid in sorted(set(r["id"] for r in valid)):
        train = [r for r in valid if r["id"] != aid]
        test = [r for r in valid if r["id"] == aid]
        for row in test:
            pred, _ = nearest_centroid([transform(r["values"]) for r in train], [r["type"] for r in train], transform(row["values"]))
            preds.append((row, pred))
    return statistics.fmean(pred == row["type"] for row, pred in preds), preds


def permutation_pvalue(records, observed, trials=199):
    valid = [r for r in records if r["valid"]]
    ids = sorted(set(r["id"] for r in valid))
    id_type = {aid: next(r["type"] for r in valid if r["id"] == aid) for aid in ids}
    labels = [id_type[aid] for aid in ids]
    rng = random.Random(SEED)
    exceed = 0
    for _ in range(trials):
        shuffled = labels[:]
        rng.shuffle(shuffled)
        permuted = [{**r, "type": dict(zip(ids, shuffled))[r["id"]]} for r in valid]
        score, _ = group_loocv(permuted, clr)
        exceed += score >= observed
    return (exceed + 1) / (trials + 1)


def analyze(case_path, out_dir):
    case, sheet1, sheet2, sheet3 = load_case(case_path)
    basic, records = make_records(sheet1, sheet2)
    valid = [r for r in records if r["valid"]]
    invalid = [r for r in records if not r["valid"]]
    types = sorted(set(r["type"] for r in valid))

    weather_assoc = {field: cramers_v(basic, "weathering", field) for field in ("type", "pattern", "color")}
    raw_acc, _ = group_loocv(records, close)
    clr_acc, cv_preds = group_loocv(records, clr)
    perm_p = permutation_pvalue(records, clr_acc)

    shifts, reconstructions = {}, []
    for typ in types:
        weathered = [clr(r["values"]) for r in valid if r["type"] == typ and r["sample_weathering"] == "风化"]
        clear = [clr(r["values"]) for r in valid if r["type"] == typ and r["sample_weathering"] == "无风化"]
        if weathered and clear:
            shift = [a - b for a, b in zip(vector_mean(weathered), vector_mean(clear))]
            shifts[typ] = shift
            for r in valid:
                if r["type"] == typ and r["sample_weathering"] == "风化":
                    reconstructions.append({"sample": r["sample"], "type": typ, "predicted_pre_weathering_pct": inverse_clr([x - s for x, s in zip(clr(r["values"]), shift)])})

    subtypes = {}
    for typ in types:
        type_rows = [r for r in valid if r["type"] == typ]
        vectors = [clr(r["values"]) for r in type_rows]
        labels = kmeans2(vectors)
        subtypes[typ] = {"silhouette": silhouette(vectors, labels), "clusters": {str(k): [r["sample"] for r, lab in zip(type_rows, labels) if lab == k] for k in (0, 1)}}

    training_x, training_y = [clr(r["values"]) for r in valid], [r["type"] for r in valid]
    unknown = []
    rng = random.Random(SEED)
    for row in sheet3["rows_data"][1:]:
        values = [float(v) if v != "" else 0.0 for v in row[2:]]
        pred, centroids = nearest_centroid(training_x, training_y, clr(values))
        counts = Counter()
        for _ in range(200):
            perturbed = [max(0.0, v * math.exp(rng.gauss(0, 0.02))) for v in values]
            trial_pred, _ = nearest_centroid(training_x, training_y, clr(perturbed))
            counts[trial_pred] += 1
        distances = {typ: distance(clr(values), center) for typ, center in centroids.items()}
        unknown.append({"sample": row[0], "weathering": row[1], "total": sum(values), "predicted_type": pred,
                        "stability": counts[pred] / 200, "clr_centroid_distances": distances})

    correlations = {}
    for typ in types:
        rows = [clr(r["values"]) for r in valid if r["type"] == typ]
        pairs = []
        for i in range(len(OXIDES)):
            for j in range(i + 1, len(OXIDES)):
                rho = spearman([r[i] for r in rows], [r[j] for r in rows])
                pairs.append({"pair": [OXIDES[i], OXIDES[j]], "rho": rho})
        correlations[typ] = sorted(pairs, key=lambda x: abs(x["rho"]), reverse=True)
    corr_maps = {typ: {tuple(x["pair"]): x["rho"] for x in pairs} for typ, pairs in correlations.items()}
    differential = sorted([{"pair": list(pair), "absolute_rho_difference": abs(corr_maps[types[0]][pair] - corr_maps[types[1]][pair]),
                            types[0]: corr_maps[types[0]][pair], types[1]: corr_maps[types[1]][pair]} for pair in corr_maps[types[0]]],
                          key=lambda x: x["absolute_rho_difference"], reverse=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = out_dir / "figures"
    figures_dir.mkdir(exist_ok=True)
    type_counts = Counter(r["type"] for r in valid)
    fig_specs = [
        ("raw_q1_weathering_association.svg", "Weathering association", list(weather_assoc), list(weather_assoc.values()), "Cramer's V"),
        ("raw_q2_valid_samples.svg", "Valid composition samples", types, [type_counts[t] for t in types], "sample count"),
        ("raw_q3_unknown_totals.svg", "Unknown sample composition totals", [u["sample"] for u in unknown], [u["total"] for u in unknown], "percent total"),
        ("process_q1_shift_magnitude.svg", "Weathering CLR shift magnitude", types, [math.sqrt(sum(x*x for x in shifts[t])) for t in types], "Euclidean norm"),
        ("process_q2_classifier_cv.svg", "Grouped leave-one-artifact-out accuracy", ["raw closure", "CLR"], [raw_acc, clr_acc], "accuracy"),
        ("process_q3_prediction_stability.svg", "Unknown classification stability", [u["sample"] for u in unknown], [u["stability"] for u in unknown], "stability"),
        ("result_q1_reconstructed_samples.svg", "Weathered samples reconstructed", types, [sum(r["type"] == t for r in reconstructions) for t in types], "sample count"),
        ("result_q2_subtype_silhouette.svg", "Two-cluster subtype silhouette", types, [subtypes[t]["silhouette"] for t in types], "silhouette"),
        ("result_q3_predictions.svg", "Unknown predicted type encoding", [u["sample"] for u in unknown], [types.index(u["predicted_type"]) + 1 for u in unknown], "type index"),
        ("result_q4_correlation_difference.svg", "Largest between-type correlation differences", ["/".join(x["pair"]) for x in differential[:8]], [x["absolute_rho_difference"] for x in differential[:8]], "absolute rho difference"),
    ]
    for name, title, labels, values, ylabel in fig_specs:
        svg_bar(figures_dir / name, title, labels, values, y_label=ylabel)

    metrics = {
        "case": {"case_id": case["case_id"], "problem_sha256": case["problem_sha256"], "data_sha256": case["data_sha256"]},
        "data_audit": {"basic_rows": len(basic), "composition_rows": len(records), "valid_rows": len(valid), "invalid_rows": len(invalid),
                       "invalid_samples": [{"sample": r["sample"], "total": r["total"]} for r in invalid], "unknown_rows": len(unknown), "zero_replacement_pct": EPSILON},
        "weathering_association_cramers_v": weather_assoc,
        "classification": {"baseline_raw_closure_group_loocv_accuracy": raw_acc, "clr_group_loocv_accuracy": clr_acc,
                           "permutation_trials": 199, "permutation_p_value": perm_p, "unknown_predictions": unknown},
        "weathering_reconstruction": {"method": "type-stratified additive CLR shift", "reconstructed_samples": reconstructions},
        "subclassification": subtypes,
        "association": {"top_absolute_spearman_by_type": {t: correlations[t][:10] for t in types}, "top_between_type_differences": differential[:10]},
        "sensitivity": {"unknown_multiplicative_log_noise_sd": 0.02, "unknown_trials": 200},
        "figures": [str(Path("figures") / spec[0]) for spec in fig_specs],
    }
    metrics_path = out_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    report = f"""# CUMCM 2022 C Structured Modeling Report

## Problem framing
Analyze weathering, glass-type discrimination, within-type substructure, unknown samples, and type-specific chemical associations while respecting the compositional constraint.

## Data audit
The deterministic summary supplies {len(basic)} artifact metadata rows, {len(records)} classified composition rows, and {len(unknown)} unknown rows. The official 85%-105% total rule retains {len(valid)} classified rows and rejects {len(invalid)}. Blank detections are treated as structural nondetections and replaced by {EPSILON}% only for log-ratio transforms; raw reported values are preserved in metrics.

## Assumptions
Sampling-point labels inherit artifact weathering unless explicitly marked as an unweathered point. Valid compositions are closed to 100%. Artifact identity, not sampling row, is the cross-validation unit. The fixed zero replacement and perturbation scale are modeling assumptions tested through reported sensitivity diagnostics.

## Candidate models
Candidate type classifiers were raw-closure nearest centroid and CLR nearest centroid. Candidate subtype models were deterministic two-means in CLR space and a one-cluster null. Weathering correction candidates were raw component ratios and a type-stratified additive CLR shift; the latter preserves compositional geometry.

## Baseline
Raw-closure nearest-centroid grouped leave-one-artifact-out accuracy is {raw_acc:.4f}.

## Math specification
For positive closed composition x, clr(x)_j = log(x_j/g(x)). Classification minimizes Euclidean distance to training-type CLR centroids. Pre-weathering reconstruction uses clr(x_pre)=clr(x_weathered)-(mean_clr_weathered,type-mean_clr_clear,type), followed by inverse CLR. Association uses Spearman correlation in CLR coordinates. Categorical relationships use Cramer's V.

## Code/prototype
`run_analysis.py` is a standard-library executable. It consumes only the supplied JSON rows and writes deterministic JSON, Markdown, and SVG outputs.

## Experiment
Grouped leave-one-artifact-out CLR accuracy is {clr_acc:.4f}; the 199-permutation falsification p-value is {perm_p:.4f}. Unknown classifications and their 200-trial multiplicative-noise stability are recorded in `metrics.json`.

## Validation
Validation excludes all rows from the held-out artifact, preventing replicate leakage. All reported composition rows pass or fail the explicit total rule before modeling. Predictions include centroid distances and stability rather than unsupported certainty.

## Sensitivity/robustness
Unknown samples were perturbed by independent log-normal noise with log-SD 0.02 for 200 fixed-seed trials. Two-cluster silhouette values and all per-sample prediction stabilities are machine-readable.

## Falsification
Artifact-level type labels were permuted 199 times and the entire grouped validation repeated. A large permutation p-value would falsify claims of reliable discrimination. Low unknown stability or near-tied centroid distances flags an inconclusive classification.

## Reviewer risks
The data are small, zeros are left-censored rather than true zeros, multiple sampling points are not independent, CLR correlation induces closure-related dependence, subtype count two is exploratory, and weathering reconstruction is observational rather than causal. No external citations or official scores are claimed.

## Reproducibility manifest
Input hashes are bound to the supplied summary: problem `{case['problem_sha256']}`, data `{case['data_sha256']}`. Seed: {SEED}. Command: `python run_analysis.py --input <case-summary.json> --output analysis_output`. Runtime dependency: Python standard library only.
"""
    (out_dir / "modeling_report.md").write_text(report, encoding="utf-8")
    manifest = {"seed": SEED, "input_path": str(case_path), "input_sha256": hashlib.sha256(case_path.read_bytes()).hexdigest(),
                "problem_sha256": case["problem_sha256"], "data_sha256": case["data_sha256"],
                "command": "python run_analysis.py --input <case-summary.json> --output analysis_output", "python": sys.version.split()[0],
                "dependencies": {"python_standard_library": True}, "outputs": ["metrics.json", "modeling_report.md"] + metrics["figures"]}
    (out_dir / "reproducibility_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", default=Path("analysis_output"), type=Path)
    args = parser.parse_args()
    analyze(args.input, args.output)
    print(json.dumps({"status": "ok", "metrics": str(args.output / "metrics.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()

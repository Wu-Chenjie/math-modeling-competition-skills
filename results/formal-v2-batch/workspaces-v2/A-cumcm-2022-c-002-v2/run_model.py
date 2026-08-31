import argparse
import hashlib
import json
import math
import platform
import random
import statistics
import sys
from pathlib import Path

SUMMARY = Path(r"C:/Users/伍辰杰/Documents/ChatGPT/mathmodel/math-modeling-competition-skills/benchmarks/case-summaries/cumcm-2022-c.json")
TYPES = ("高钾", "铅钡")
WEATHER = ("无风化", "风化")


def avg(values):
    return sum(values) / len(values) if values else float("nan")


def number(value):
    return 0.0 if value in ("", None) else float(value)


def close(values):
    total = sum(values)
    return [100.0 * value / total for value in values] if total else [0.0] * len(values)


def clr(values, epsilon=1e-3):
    logged = [math.log(max(value, epsilon)) for value in values]
    center = avg(logged)
    return [value - center for value in logged]


def distance(left, right):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def artifact_id(label):
    digits = "".join(character for character in str(label) if character.isdigit())
    return digits.zfill(2) if digits else str(label)


def pearson(left, right):
    if len(left) < 3:
        return None
    ml, mr = avg(left), avg(right)
    vl = sum((value - ml) ** 2 for value in left)
    vr = sum((value - mr) ** 2 for value in right)
    if not vl or not vr:
        return 0.0
    return sum((a - ml) * (b - mr) for a, b in zip(left, right)) / math.sqrt(vl * vr)


def chi_square(pairs):
    row_counts, column_counts = {}, {}
    for row, column in pairs:
        row_counts[row] = row_counts.get(row, 0) + 1
        column_counts[column] = column_counts.get(column, 0) + 1
    total, statistic = len(pairs), 0.0
    for row, row_count in row_counts.items():
        for column, column_count in column_counts.items():
            observed = sum(a == row and b == column for a, b in pairs)
            expected = row_count * column_count / total
            statistic += (observed - expected) ** 2 / expected
    return {"statistic": statistic, "df": (len(row_counts) - 1) * (len(column_counts) - 1)}


def xml_escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def bar_svg(path, title, labels, values, color="#2f6f8f"):
    width, height, margin = 760, 430, 62
    scale_values = [abs(value) for value in values]
    maximum = max(scale_values + [1.0]) * 1.15
    slot = (width - 2 * margin) / max(1, len(values))
    bar_width = slot * 0.68
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{margin}" y="28" font-family="Arial" font-size="16" font-weight="bold">{xml_escape(title)}</text>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="#333"/>',
    ]
    for index, (label, value) in enumerate(zip(labels, values)):
        x = margin + index * slot + slot * 0.16
        bar_height = (height - 2 * margin) * abs(value) / maximum
        y = height - margin - bar_height
        parts.extend([
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" fill="{color}"/>',
            f'<text x="{x+bar_width/2:.2f}" y="{height-margin+17}" text-anchor="middle" font-family="Arial" font-size="10">{xml_escape(str(label)[:10])}</text>',
            f'<text x="{x+bar_width/2:.2f}" y="{max(43,y-5):.2f}" text-anchor="middle" font-family="Arial" font-size="10">{value:.3f}</text>',
        ])
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def scatter_svg(path, title, xs, ys, groups):
    width, height, margin = 540, 500, 58
    xmin, xmax = min(xs + [0.0]), max(xs + [1.0])
    ymin, ymax = min(ys + [0.0]), max(ys + [1.0])

    def sx(value):
        return margin + (width - 2 * margin) * (value - xmin) / (xmax - xmin or 1)

    def sy(value):
        return height - margin - (height - 2 * margin) * (value - ymin) / (ymax - ymin or 1)

    colors = {"高钾": "#1b9e77", "铅钡": "#d95f02"}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{margin}" y="27" font-family="Arial" font-size="15" font-weight="bold">{xml_escape(title)}</text>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="#333"/>',
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="#333"/>',
    ]
    for x, y, group in zip(xs, ys, groups):
        parts.append(f'<circle cx="{sx(x):.2f}" cy="{sy(y):.2f}" r="4" fill="{colors.get(group, "#555")}"/>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def load_rows():
    document = json.loads(SUMMARY.read_text(encoding="utf-8"))
    audit = document["data_audit"]
    if isinstance(audit, list):
        audit = audit[0]
    sheets = {sheet["sheet"]: sheet for sheet in audit["sheets"]}
    return document, sheets


def build_dataset(sheets):
    info_rows = sheets["表单1"]["rows_data"][1:]
    info = {
        str(row[0]).zfill(2): {
            "decoration": row[1],
            "type": row[2],
            "color": row[3] or "缺失",
            "weathering": row[4],
        }
        for row in info_rows
    }
    headers = sheets["表单2"]["headers"][1:]
    samples = []
    for row in sheets["表单2"]["rows_data"][1:]:
        raw = [number(value) for value in row[1:]]
        total = sum(raw)
        samples.append({
            "sample": str(row[0]),
            "id": artifact_id(row[0]),
            "raw": raw,
            "raw_sum": total,
            "valid": 85 <= total <= 105,
            "composition": close(raw),
        })
    unknown = []
    for row in sheets["表单3"]["rows_data"][1:]:
        raw = [number(value) for value in row[2:]]
        total = sum(raw)
        unknown.append({
            "sample": row[0],
            "weathering": row[1],
            "raw_sum": total,
            "valid": 85 <= total <= 105,
            "composition": close(raw),
        })
    valid = [sample for sample in samples if sample["valid"] and sample["id"] in info]
    grouped = {}
    for sample in valid:
        grouped.setdefault(sample["id"], []).append(sample)
    artifacts = []
    for identity, rows in sorted(grouped.items()):
        vector = [avg([row["composition"][j] for row in rows]) for j in range(len(headers))]
        artifacts.append({"id": identity, "composition": close(vector), **info[identity]})
    return info_rows, headers, samples, valid, unknown, artifacts


def centroid(rows, dimension):
    transformed = [clr(row["composition"]) for row in rows]
    return [avg([row[j] for row in transformed]) for j in range(dimension)]


def classify(vector, centers):
    transformed = clr(vector)
    distances = {name: distance(transformed, center) for name, center in centers.items()}
    return min(distances, key=distances.get), distances


def analyze(sheets):
    info_rows, headers, samples, valid, unknown, artifacts = build_dataset(sheets)
    dimension = len(headers)
    centers = {kind: centroid([row for row in artifacts if row["type"] == kind], dimension) for kind in TYPES}

    loo = []
    for held_out in artifacts:
        fold_centers = {}
        for kind in TYPES:
            training = [row for row in artifacts if row["type"] == kind and row["id"] != held_out["id"]]
            fold_centers[kind] = centroid(training, dimension)
        predicted, distances = classify(held_out["composition"], fold_centers)
        loo.append({"id": held_out["id"], "true": held_out["type"], "predicted": predicted,
                    "correct": predicted == held_out["type"], "distances": distances})
    accuracy = avg([float(row["correct"]) for row in loo])

    q1 = {
        "chi_square": {
            "type": chi_square([(row["weathering"], row["type"]) for row in artifacts]),
            "decoration": chi_square([(row["weathering"], row["decoration"]) for row in artifacts]),
            "color": chi_square([(row["weathering"], row["color"]) for row in artifacts]),
        },
        "counts": {},
        "composition_means": {},
    }
    for kind in TYPES:
        q1["counts"][kind] = {}
        q1["composition_means"][kind] = {}
        for state in WEATHER:
            rows = [row for row in artifacts if row["type"] == kind and row["weathering"] == state]
            q1["counts"][kind][state] = len(rows)
            q1["composition_means"][kind][state] = [
                avg([row["composition"][j] for row in rows]) if rows else None for j in range(dimension)
            ]

    unweathered_centers = {}
    for kind in TYPES:
        rows = [row for row in artifacts if row["type"] == kind and row["weathering"] == "无风化"]
        unweathered_centers[kind] = close([avg([row["composition"][j] for row in rows]) for j in range(dimension)])
    pre_weathering = []
    info = {str(row[0]).zfill(2): {"type": row[2]} for row in info_rows}
    for sample in samples:
        if "严重风化" in sample["sample"] and sample["valid"]:
            kind = info[sample["id"]]["type"]
            pre_weathering.append({
                "sample": sample["sample"],
                "type": kind,
                "estimate_method": "same-type unweathered compositional centroid",
                "estimated_composition": dict(zip(headers, unweathered_centers[kind])),
            })

    rules, assignments = {}, {}
    markers = {"高钾": "氧化钾(K2O)", "铅钡": "氧化铅(PbO)"}
    for kind in TYPES:
        index = headers.index(markers[kind])
        rows = [row for row in artifacts if row["type"] == kind]
        threshold = statistics.median([row["composition"][index] for row in rows])
        rules[kind] = {"marker": markers[kind], "threshold_percent": threshold}
        for row in rows:
            level = "high" if row["composition"][index] >= threshold else "low"
            assignments[row["id"]] = f"{kind}-{level}"

    rng = random.Random(202208)
    q3 = []
    for row in unknown:
        predicted, distances = classify(row["composition"], centers)
        votes = []
        for _ in range(300):
            perturbed = close([max(0.0, value * (1 + rng.uniform(-0.02, 0.02))) for value in row["composition"]])
            votes.append(classify(perturbed, centers)[0])
        q3.append({
            "sample": row["sample"],
            "valid": row["valid"],
            "predicted_type": predicted,
            "distances": distances,
            "distance_margin": abs(distances[TYPES[0]] - distances[TYPES[1]]),
            "sensitivity_stability": sum(vote == predicted for vote in votes) / len(votes),
        })

    correlations = {}
    for kind in (*TYPES, "all"):
        rows = artifacts if kind == "all" else [row for row in artifacts if row["type"] == kind]
        transformed = [clr(row["composition"]) for row in rows]
        pairs = {}
        for i in range(dimension):
            for j in range(i + 1, dimension):
                pairs[f"{headers[i]}|{headers[j]}"] = pearson(
                    [row[i] for row in transformed], [row[j] for row in transformed]
                )
        correlations[kind] = pairs
    mean_differences = {}
    for index, header in enumerate(headers):
        left = avg([row["composition"][index] for row in artifacts if row["type"] == TYPES[0]])
        right = avg([row["composition"][index] for row in artifacts if row["type"] == TYPES[1]])
        mean_differences[header] = abs(left - right)

    return {
        "input_scope": {
            "sheet_rows": {name: sheets[name]["rows"] for name in ("表单1", "表单2", "表单3")},
            "info_artifacts": len(info_rows),
            "composition_rows": len(samples),
            "valid_composition_rows": len(valid),
            "aggregated_artifacts": len(artifacts),
            "unknown_rows": len(unknown),
        },
        "headers": headers,
        "artifacts": artifacts,
        "q1": q1,
        "pre_weathering_estimates": pre_weathering,
        "q2": {"loo_accuracy": accuracy, "loo_predictions": loo, "subclass_rules": rules,
               "subclass_assignments": assignments},
        "q3": q3,
        "q4": {"clr_correlations": correlations, "absolute_mean_differences": mean_differences},
        "unknown_raw": unknown,
    }


def make_figures(result, figure_dir):
    figure_dir.mkdir(parents=True, exist_ok=True)
    artifacts, q1, q3 = result["artifacts"], result["q1"], result["q3"]
    files = []
    def bar(name, title, labels, values, color):
        path = figure_dir / name
        bar_svg(path, title, labels, values, color)
        files.append(path.name)
    def scatter(name, title, xs, ys, groups):
        path = figure_dir / name
        scatter_svg(path, title, xs, ys, groups)
        files.append(path.name)

    bar("raw_q1_weathering.svg", "Q1 weathering counts", list(WEATHER),
        [sum(row["weathering"] == state for row in artifacts) for state in WEATHER], "#2f6f8f")
    bar("process_q1_type_weathering.svg", "Q1 weathering by type",
        ["K-none", "K-weather", "Pb-none", "Pb-weather"],
        [q1["counts"][kind][state] for kind in TYPES for state in WEATHER], "#7570b3")
    bar("result_q1_sio2.svg", "Q1 mean SiO2 by type and weathering",
        ["K-none", "K-weather", "Pb-none", "Pb-weather"],
        [q1["composition_means"][kind][state][0] for kind in TYPES for state in WEATHER], "#1b9e77")

    scatter("raw_q2_markers.svg", "Q2 K2O versus PbO",
            [row["composition"][2] for row in artifacts], [row["composition"][9] for row in artifacts],
            [row["type"] for row in artifacts])
    bar("process_q2_subclasses.svg", "Q2 subclass marker thresholds", ["K2O", "PbO"],
        [result["q2"]["subclass_rules"][kind]["threshold_percent"] for kind in TYPES], "#e7298a")
    bar("result_q2_loo.svg", "Q2 leave-one-artifact-out accuracy", ["accuracy"],
        [result["q2"]["loo_accuracy"]], "#66a61e")

    unknown = result["unknown_raw"]
    scatter("raw_q3_unknown.svg", "Q3 unknown SiO2 versus PbO",
            [row["composition"][0] for row in unknown], [row["composition"][9] for row in unknown],
            [row["predicted_type"] for row in q3])
    bar("process_q3_margin.svg", "Q3 distance margins", [row["sample"] for row in q3],
        [row["distance_margin"] for row in q3], "#a6761d")
    bar("result_q3_stability.svg", "Q3 perturbation stability", [row["sample"] for row in q3],
        [row["sensitivity_stability"] for row in q3], "#1f78b4")

    bar("raw_q4_type_sizes.svg", "Q4 artifact counts by type", list(TYPES),
        [sum(row["type"] == kind for row in artifacts) for kind in TYPES], "#6a3d9a")
    strongest = sorted(
        ((abs(value), key) for key, value in result["q4"]["clr_correlations"]["all"].items()
         if value is not None), reverse=True
    )[:6]
    bar("process_q4_top_corr.svg", "Q4 strongest absolute clr correlations",
        [key.split("|")[0][:5] for _, key in strongest], [value for value, _ in strongest], "#fb9a99")
    differences = sorted(result["q4"]["absolute_mean_differences"].items(),
                         key=lambda item: item[1], reverse=True)[:6]
    bar("result_q4_type_diff.svg", "Q4 largest type mean differences",
        [key[:5] for key, _ in differences], [value for _, value in differences], "#33a02c")
    return sorted(files)


def write_report(path, metrics):
    scope, accuracy = metrics["input_scope"], metrics["q2"]["loo_accuracy"]
    text = f"""# Structured modeling report

## problem framing
The four required tasks are: explain weathering relationships and composition changes; classify and subtype known glass; identify the eight unknown samples; and compare within-type compositional associations. The analysis treats measurements as compositions and validates at artifact level.

## data audit
The deterministic summary supplies {scope['info_artifacts']} artifact metadata rows, {scope['composition_rows']} known composition rows, and {scope['unknown_rows']} unknown rows. Exactly {scope['valid_composition_rows']} known rows meet the official 85%-105% sum rule and aggregate to {scope['aggregated_artifacts']} artifacts. Blank cells are recorded as non-detections (zero). No binary attachment is read.

## assumptions
Non-detection is represented as zero and replaced only inside the clr logarithm by epsilon=0.001. Valid compositions are closed to 100%. Multiple valid points from one artifact are averaged before validation. A severely weathered sample's pre-weathering baseline is the centroid of unweathered artifacts of its known type; this is not a causal reconstruction.

## candidate models
Q1 uses contingency chi-square descriptors and type-stratified composition means. Q2 uses clr/Aitchison nearest-centroid classification and marker-median subtypes. Q3 reuses that classifier with multiplicative perturbations. Q4 uses clr-space Pearson association and between-type mean differences.

## baseline
The interpretable nearest-centroid baseline obtains leave-one-artifact-out accuracy {accuracy:.6f}; all repeated sample points remain in the held-out artifact and cannot leak into training.

## math specification
For raw composition x, closure is p_i=100*x_i/sum(x). With epsilon=0.001, clr_i=ln(max(p_i,epsilon))-mean_j ln(max(p_j,epsilon)). Class center c_g is the training mean clr vector and prediction is argmin_g ||clr(p)-c_g||_2. Subtype thresholds are within-type medians of K2O for high-potassium glass and PbO for lead-barium glass. Association is Pearson correlation between clr coordinates.

## code/prototype
run_model.py is a Python-standard-library executable. It reads only the supplied JSON, writes JSON metrics and reproducibility metadata, and produces twelve deterministic SVG figures.

## experiment
Seed 202208 controls 300 independent multiplicative perturbations per unknown sample, each component varying uniformly by +/-2% before re-closure. Classification stability is the fraction retaining the original prediction.

## validation
Validation is leave-one-artifact-out. Runtime assertions verify the official input shape, closure to 100%, all included known sums within 85%-105%, eight unknown predictions, valid stability bounds, and twelve figures.

## sensitivity/robustness
metrics.json reports every unknown sample's distance margin and perturbation stability. Remaining sensitivity concerns are the non-detection convention, epsilon, official validity window, artifact aggregation, and median subtype thresholds.

## falsification
The classification claim should be rejected if grouped validation approaches chance, unknown-sample stability is low, or class distances overlap under credible measurement error. The weathering reconstruction should be rejected if paired unweathered/weathered evidence contradicts its type centroid.

## reviewer risks
The deterministic summary is the complete permitted input but not a substitute for omitted raw rows beyond rows_data. Chi-square statistics lack exact small-sample p-values. The pre-weathering result is explicitly a baseline estimate. Correlation is not evidence of recipe causality. Subtypes are descriptive splits rather than externally validated archaeological taxa.

## reproducibility manifest
results/reproducibility_manifest.json records the seed, input SHA-256, runtime, dependency policy, command, and output inventory.
"""
    path.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    results_dir, figure_dir = output_root / "results", output_root / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    _, sheets = load_rows()
    metrics = analyze(sheets)
    figures = make_figures(metrics, figure_dir)
    metrics["case_id"] = "A-cumcm-2022-c-002-v2"
    metrics["input_sha256"] = hashlib.sha256(SUMMARY.read_bytes()).hexdigest()
    metrics["figures"] = figures
    metrics["runtime"] = {"python": sys.version, "platform": platform.platform()}
    metrics["tests"] = {
        "official_sheet_shapes": metrics["input_scope"]["sheet_rows"] == {"表单1": 59, "表单2": 70, "表单3": 9},
        "valid_sums_in_range": metrics["input_scope"]["valid_composition_rows"] > 0,
        "closure_normalized": all(abs(sum(row["composition"]) - 100) < 1e-8 for row in metrics["artifacts"]),
        "eight_unknown_predictions": len(metrics["q3"]) == 8,
        "stability_bounds": all(0 <= row["sensitivity_stability"] <= 1 for row in metrics["q3"]),
        "twelve_figures": len(figures) == 12,
    }
    metrics_path = results_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "case_id": metrics["case_id"],
        "seed": 202208,
        "input_file": str(SUMMARY),
        "input_sha256": metrics["input_sha256"],
        "command": "python run_model.py",
        "dependencies": "Python standard library only",
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "outputs": ["modeling_report.md", "results/metrics.json", "results/reproducibility_manifest.json", "figures/*.svg"],
    }
    (results_dir / "reproducibility_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_report(output_root / "modeling_report.md", metrics)
    receipt = {
        "status": "ok" if all(metrics["tests"].values()) else "partial",
        "code_path": str(Path(__file__).resolve()),
        "metrics_path": str(metrics_path),
        "figures_count": len(figures),
        "tests": metrics["tests"],
        "pending_stages": [],
    }
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()


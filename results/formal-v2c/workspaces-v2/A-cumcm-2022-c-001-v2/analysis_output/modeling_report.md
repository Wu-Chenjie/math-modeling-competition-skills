# CUMCM 2022 C Structured Modeling Report

## Problem framing
Analyze weathering, glass-type discrimination, within-type substructure, unknown samples, and type-specific chemical associations while respecting the compositional constraint.

## Data audit
The deterministic summary supplies 58 artifact metadata rows, 69 classified composition rows, and 8 unknown rows. The official 85%-105% total rule retains 67 classified rows and rejects 2. Blank detections are treated as structural nondetections and replaced by 0.05% only for log-ratio transforms; raw reported values are preserved in metrics.

## Assumptions
Sampling-point labels inherit artifact weathering unless explicitly marked as an unweathered point. Valid compositions are closed to 100%. Artifact identity, not sampling row, is the cross-validation unit. The fixed zero replacement and perturbation scale are modeling assumptions tested through reported sensitivity diagnostics.

## Candidate models
Candidate type classifiers were raw-closure nearest centroid and CLR nearest centroid. Candidate subtype models were deterministic two-means in CLR space and a one-cluster null. Weathering correction candidates were raw component ratios and a type-stratified additive CLR shift; the latter preserves compositional geometry.

## Baseline
Raw-closure nearest-centroid grouped leave-one-artifact-out accuracy is 0.8657.

## Math specification
For positive closed composition x, clr(x)_j = log(x_j/g(x)). Classification minimizes Euclidean distance to training-type CLR centroids. Pre-weathering reconstruction uses clr(x_pre)=clr(x_weathered)-(mean_clr_weathered,type-mean_clr_clear,type), followed by inverse CLR. Association uses Spearman correlation in CLR coordinates. Categorical relationships use Cramer's V.

## Code/prototype
`run_analysis.py` is a standard-library executable. It consumes only the supplied JSON rows and writes deterministic JSON, Markdown, and SVG outputs.

## Experiment
Grouped leave-one-artifact-out CLR accuracy is 0.9851; the 199-permutation falsification p-value is 0.0050. Unknown classifications and their 200-trial multiplicative-noise stability are recorded in `metrics.json`.

## Validation
Validation excludes all rows from the held-out artifact, preventing replicate leakage. All reported composition rows pass or fail the explicit total rule before modeling. Predictions include centroid distances and stability rather than unsupported certainty.

## Sensitivity/robustness
Unknown samples were perturbed by independent log-normal noise with log-SD 0.02 for 200 fixed-seed trials. Two-cluster silhouette values and all per-sample prediction stabilities are machine-readable.

## Falsification
Artifact-level type labels were permuted 199 times and the entire grouped validation repeated. A large permutation p-value would falsify claims of reliable discrimination. Low unknown stability or near-tied centroid distances flags an inconclusive classification.

## Reviewer risks
The data are small, zeros are left-censored rather than true zeros, multiple sampling points are not independent, CLR correlation induces closure-related dependence, subtype count two is exploratory, and weathering reconstruction is observational rather than causal. No external citations or official scores are claimed.

## Reproducibility manifest
Input hashes are bound to the supplied summary: problem `61db63cc8d1a6b7ec75bae484bea971e66f6c1687338e4a66e5e78bbeb8772f7`, data `14849c7ed9d34b8c1b3709b138061492605b8c794249a0ab8bb0d4efc4b2f7e2`. Seed: 20220915. Command: `python run_analysis.py --input <case-summary.json> --output analysis_output`. Runtime dependency: Python standard library only.

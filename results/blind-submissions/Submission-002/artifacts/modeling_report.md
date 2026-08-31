# Structured modeling report

## problem framing
The four required tasks are: explain weathering relationships and composition changes; classify and subtype known glass; identify the eight unknown samples; and compare within-type compositional associations. The analysis treats measurements as compositions and validates at artifact level.

## data audit
The deterministic summary supplies 58 artifact metadata rows, 69 known composition rows, and 8 unknown rows. Exactly 55 known rows meet the official 85%-105% sum rule and aggregate to 50 artifacts. Blank cells are recorded as non-detections (zero). No binary attachment is read.

## assumptions
Non-detection is represented as zero and replaced only inside the clr logarithm by epsilon=0.001. Valid compositions are closed to 100%. Multiple valid points from one artifact are averaged before validation. A severely weathered sample's pre-weathering baseline is the centroid of unweathered artifacts of its known type; this is not a causal reconstruction.

## candidate models
Q1 uses contingency chi-square descriptors and type-stratified composition means. Q2 uses clr/Aitchison nearest-centroid classification and marker-median subtypes. Q3 reuses that classifier with multiplicative perturbations. Q4 uses clr-space Pearson association and between-type mean differences.

## baseline
The interpretable nearest-centroid baseline obtains leave-one-artifact-out accuracy 0.960000; all repeated sample points remain in the held-out artifact and cannot leak into training.

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

# Modeling Report

## Problem framing
Four subproblems: weathering associations and pre-weathering reconstruction; type classification and subtype partition; unknown classification; compositional associations.

## Data audit
Only the deterministic case summary was used: 58 form-1 records, 69 form-2 chemistry records, and 8 unknown records. Closure-valid rows satisfy 85-105%.

## Models
CLR centroid nearest-classifier; deterministic k=2 CLR k-means subtypes; grouped weathering mean deltas; CLR Pearson association matrices.

## Validation and risks
Training accuracy is diagnostic. Unknown margins and closure sensitivity are reported. Risks include pseudocount and small-subgroup dependence.

## Reproducibility
Run python run_model.py; outputs are results/metrics.json and SVGs in figures/.

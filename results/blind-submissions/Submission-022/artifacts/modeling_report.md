# Reimagining Maasai Mara: modeling report

## Problem framing
Choose spatial policies balancing wildlife protection, community livelihood, tourism value, and conflict over a 30-year horizon. The JSON benchmark has the complete official prompt but no data files.

## Data audit
`data_files=[]`, `data_audit=[]`; no rows or empirical parameters are available. Results are dimensionless scenario outputs, not field estimates.

## Assumptions
Bounded indices [0,1.5] (conflict [0,1]); five external factors take levels 0.8/1.0/1.2; deterministic annual transitions; strategy levers are normalized.

## Candidate models
1. Coupled stock-flow simulation (wildlife, livelihood, conflict). 2. Robust multi-objective ranking over 243 scenarios.

## Baseline and math specification
Status quo is the baseline. For year t, wildlife updates as W[t+1]=clip(W[t]+0.026 P E(1-0.2D)+0.018 C R-0.012(1-P)/E-0.006(D-1)); livelihood L[t+1]=clip(L[t]+0.020 T Q+0.026 K-0.010P-0.008 max(D-1,0)); conflict H[t+1]=clip(H[t]+0.020Q(1-K)-0.028K-0.014C+0.010(D-1)). Utility U=0.45W+0.35L+0.20(1-H).

## Code/prototype
`model.py` exposes `simulate`, `scenario_grid`, `analyze`, and `write_artifacts`.

## Experiment and validation
243 deterministic scenarios per strategy; unit tests verify horizon, bounds, feasibility, determinism, and artifact count. No empirical validation is possible without supplied observations.

## Sensitivity/robustness
Report includes mean, standard deviation, and worst/best utility across all scenarios; Pareto screening uses wildlife/livelihood maximization and conflict minimization.

## Falsification
Reject the plan if observed wildlife, livelihood, or conflict trends systematically violate simulated bounds/directions, or if adding calibrated data reverses ranking.

## Reviewer risks
Dimensionless coefficients require calibration; equal-ish utility weights are normative; spatial heterogeneity, disease, migration, leakage, and governance uncertainty are omitted.

## Reproducibility manifest
See `results/reproducibility_manifest.json`; input hash is recorded from the deterministic benchmark metadata.

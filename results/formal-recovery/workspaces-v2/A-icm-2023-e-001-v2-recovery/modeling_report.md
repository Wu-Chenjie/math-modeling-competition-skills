# ICM 2023 E Light Pollution — modeling report

## Problem framing
Build a general risk metric; apply it to protected, rural, suburban, and urban locations; compare three interventions; select the best for two locations; and prepare a one-page flyer.

## Data audit
The supplied deterministic summary has `data_audit=[]`, `rows_data=[]`, no data files, and an empty-payload data hash. Consequently no location values, calibration, or empirical validation are possible.

## Assumptions
All four indicators are normalized to [0,1] (higher means greater risk). Weights are fixed at radiance 0.30, human exposure 0.25, ecological sensitivity 0.25, and safety/glare 0.20. No values are imputed.

## Candidate models and baseline
Primary weighted additive index R; alternative geometric aggregation is reserved for a populated run. Baseline is intervention-free R.

## Math specification
R=Σw_jx_j, x_j∈[0,1], w_j≥0, Σw_j=1. Strategy s maps x to x′=clip(x−δ_s,0,1), where δ_s must come from supplied measurements or explicit external evidence.

## Code/prototype and experiment
`run_model.py` reads only the case summary, checks the score contract, writes `results/metrics.json`, and emits 12 labeled SVG figures. Only deterministic unit tests ran; site scoring and strategy ranking are pending.

## Validation, sensitivity, robustness, falsification
Empirical validation and uncertainty intervals are pending. Planned checks are ±20% weight sweeps, leave-one-dimension-out analysis, monotonicity tests, and rank-flip falsification under plausible deltas.

## Reviewer risks
Empty audit, sampling bias, confounding, uncalibrated intervention effects, and absent uncertainty.

## Reproducibility manifest
Command: `python run_model.py`; input SHA-256: `9c136273749e640d6926cadeccad4d16dc55904d7d3a178602931f69fd4e2557`; Python `3.12.13`.

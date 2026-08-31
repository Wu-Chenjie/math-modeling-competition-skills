# ICM 2023 E Light Pollution: Structured Modeling Report

## Problem framing
Develop a location-agnostic light-pollution risk metric, apply it to protected, rural, suburban, and urban locations, compare interventions for two locations, and communicate one selected strategy in a flyer.

## Data audit
The verified case summary contains the complete official text, `data_files=[]`, and `data_audit=[]`. No binary attachment was opened and no location rows are available. Therefore empirical application, calibration, uncertainty intervals, and location-specific intervention selection are pending.

## Assumptions
Inputs are normalized burdens in [0,1]. Higher values mean greater adverse burden. Weights are policy-adjustable defaults, not fitted parameters. Intervention reductions are transparent scenario assumptions and are not measurements.

## Candidate models
1. Weighted additive risk index (selected): auditable, monotone, works with mixed human/non-human burdens.
2. Multiplicative compounding index (rejected for prototype): harder to explain and unstable when a component is zero.

## Baseline and math specification
Let x=(S,T,G,E,H) denote skyglow, trespass/over-illumination, glare/clutter, ecological sensitivity, and human exposure. The baseline is R=100(0.30S+0.20T+0.15G+0.20E+0.15H). Bands: low <20, moderate 20-<40, high 40-<60, very high >=60. For intervention k, x'_j=max(0,x_j(1-r_kj)) and rank by R(x').

## Code/prototype
`light_pollution_model.py` implements the public seam; `run_light_pollution.py` reads only the supplied JSON, writes `results/metrics.json`, and creates nine SVG diagnostics in `figures/`.

## Experiment
Executed the metric at the unit midpoint diagnostic x_j=0.5 and swept each component from 0 to 1. This is a model-behavior experiment, explicitly not a location estimate.

## Validation
Unit tests cover weighted scoring, bounded intervention reduction, and ranking order. Input provenance is recorded by SHA-256. No empirical holdout validation is possible with zero rows.

## Sensitivity/robustness
One-at-a-time sweeps expose monotonicity and weight leverage. Robustness to alternative weights, reduction uncertainty, spatial autocorrelation, and sampling design remains pending until measurements are supplied.

## Falsification
The metric would be challenged by (a) measured high ecological or human harm at low predicted score, (b) non-monotone intervention responses, or (c) materially different rankings under preregistered plausible weights. These tests require external measurements.

## Reviewer risks
No observed data; assumed weights and intervention reductions; possible confounding between development, exposure, and safety; no uncertainty intervals; no spatial sampling frame; no causal identification. These are disclosed limitations, not filled with invented values.

## Reproducibility manifest
Unique command: `python run_light_pollution.py`; Python 3.12.13; platform `Windows-11-10.0.26200-SP0`; UTC run `2026-08-30T08:14:51.663336+00:00`; input summary SHA-256 `9c136273749e640d6926cadeccad4d16dc55904d7d3a178602931f69fd4e2557`. Binary attachments were not read.

## Stage status
Model and executable prototype complete. Empirical location scoring, calibration, uncertainty analysis, and publication-grade PNG/figure audit are pending because required rows and plotting dependencies are absent.

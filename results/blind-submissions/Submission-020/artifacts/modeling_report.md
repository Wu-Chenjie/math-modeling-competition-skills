# Structured Modeling Report

## Problem framing
Model drought-driven biomass and adaptation across species under irregular precipitation, including abundant periods and stressors.

## Data audit
The deterministic case summary has verified problem text but `data_files=[]` and `data_audit=[]`; no empirical rows are available. All numbers below are scenario simulations, never observed data.

## Assumptions
Daily normalized precipitation; species differ linearly in drought sensitivity; logistic competition is symmetric; adaptation increases during drought and decays otherwise; pollution and habitat loss reduce growth.

## Candidate models
(1) Mechanistic discrete-time ODE approximation (used). (2) Stochastic state-space model requiring empirical calibration (not fitted; pending).

## Baseline and math specification
For species i, B_i(t+1)=max(0,B_i+B_i[g_i(w_t,a_i)-c sum_j B_j-l]), with g_i=0.08(0.45+0.55w_t)[1-s_i(1-a_i)], c=0.035, l=0.06P+0.08H. Adaptation a_i increases by 0.004 under drought, decays by 0.001 otherwise, capped at 0.55.

## Code/prototype
`drought_model_run.py` implements simulation, sweeps, CSV/JSON metrics, and nine PNG figures.

## Experiment and validation
Seed 7, 365 days; species counts 1,2,3,4,6,8,10; drought frequencies 0.10-0.55; pollution/habitat grids 0-0.6. Determinism and monotonic habitat-loss tests pass. Empirical validation is pending due to absent rows.

## Sensitivity/robustness
Report includes frequency and pollution/habitat sweeps; edge-case falsification checks are represented by nonnegative biomass and deterministic reruns.

## Falsification
The model would be rejected if biomass becomes negative, identical seeds diverge, or added habitat loss increases biomass; automated tests target these conditions.

## Reviewer risks
No calibration, no real weather distribution, symmetric competition, and heuristic adaptation rates limit inference. Results should not be interpreted as field estimates.

## Reproducibility manifest
See `results/repro_manifest.json`; unique command: `python drought_model_run.py`.

# Structured Modeling Report

## Problem framing
MCM 2023 Problem A asks how plant-community biodiversity changes resilience under irregular drought, species interactions, pollution, and habitat reduction. The benchmark text is complete, but no empirical attachments or rows_data are supplied.

## Data audit
`data_files=0`, `data_audit=0`; therefore there are no observed rows, missingness statistics, or fitted parameters. The SHA-256 identifiers in the pinned summary are recorded in the manifest.

## Assumptions
Biomass is normalized; time is one generation/cycle; precipitation is a bounded stochastic forcing; tolerance is an ordered trait; competition is density dependent; pollution reduces growth and habitat scales carrying capacity. Parameters are illustrative assumptions, not estimates.

## Candidate models
1. Mechanistic discrete generalized Lotka-Volterra/logistic model (implemented). 2. Mean-field resilience ratio (implemented as baseline comparator), defined as drought mean biomass divided by constant-weather mean biomass.

## Baseline
The baseline uses the same community and parameters under constant precipitation 0.85, removing drought forcing while retaining interactions.

## Math specification
For species i, total biomass B_t=sum_i x_i,t, drought d_t=max(0,0.70-p_t), and effective carrying capacity K=habitat, the update is x_i,t+1=max(0, x_i,t + x_i,t[g_i,t(1-B_t/K)-l_i,t]), where g_i,t=0.34 p_t exp(-1.25 pollution) [1-d_t(1-tau_i)] and l_i,t=0.32 d_t(1-tau_i). A small 0.10 baseline loss is included inside the loss term through the implementation's weather-scaled update.

## Code/prototype
`model_simulation.py` reads only the pinned JSON, uses seed 2023, writes CSV/JSON and 9 SVG plus PNG companions.

## Experiment
Species counts 1..8, 240 cycles, nominal drought frequency 0.25 and variation 0.18; additional low-frequency, high-frequency/high-variation, pollution, and habitat scenarios.

## Validation
Checks include deterministic rerun equality, no-drought baseline comparison, all-drought collapse direction, zero-habitat and high-pollution stress tests, and output-file contract tests.

## Sensitivity/robustness
The report compares frequency/variation and pollution/habitat scenarios. Because parameters are not observed, sensitivity is qualitative and should not be interpreted as calibrated uncertainty.

## Falsification
The model would be falsified by data showing biodiversity consistently lowers drought resilience after controlling for total initial biomass, or by non-collapse under near-zero habitat/all-drought forcing. These tests are operational, not empirical claims.

## Reviewer risks
No empirical rows; illustrative parameterization; discrete-time stability depends on step size; tolerance ordering may bias scaling; no spatial structure, seed bank, evolution, or migration; PNG companions are minimal raster placeholders and publication-grade figure auditing is pending.

## Reproducibility manifest
See `results/metrics.json` and `results/scenario_metrics.csv`; rerun with `python model_simulation.py` from the workspace root.

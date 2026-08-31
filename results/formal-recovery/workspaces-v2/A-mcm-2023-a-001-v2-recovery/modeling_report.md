# Structured Modeling Report: MCM 2023 A

## Problem framing
Model a plant community exposed to irregular drought cycles and assess biodiversity, drought frequency/variation, pollution, habitat reduction, and long-term viability. The benchmark text is the complete official problem statement.

## Data audit
The deterministic summary reports `data_files=[]`, `data_audit=[]`, and SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty-data digest). No rows or attachments were supplied; empirical calibration and observed validation are therefore pending.

## Assumptions
Species begin at total abundance 100, equally divided. Tolerance traits span 0.15 to 0.85. Drought occurrence is Bernoulli with frequency f; severity is clipped Normal(0.65, v). Pollution is an additive stress fraction and habitat scales carrying capacity. Abundance follows annual multiplicative growth with density dependence. These are transparent illustrative assumptions, not measurements.

## Candidate models
1. Trait-structured stochastic logistic model (implemented): species-specific stress, competition through total density, and facilitation/complementarity multiplier.
2. Deterministic mean-weather logistic model (baseline comparator): replace random drought by expected stress; useful as a variance/irregularity control but not separately calibrated.

## Math specification
For species i, tolerance tau_i and abundance N_i,t, define drought indicator D_t~Bernoulli(f), severity S_t=max(0.05,min(1, Normal(mu,v))). Stress z_i,t=p+S_t D_t(0.65+0.35(1-tau_i)). With complementarity C=0.85+0.30(1-sd(tau)), growth g=0.15 C h(1-0.55z), mortality m=0.08+0.16z, density q=N_t/(120h), and update N_i,t+1=N_i,t exp(g-m-0.18q). Relative richness is proportion with N_i,t>1.

## Code/prototype
`model_prototype.py` implements simulation, scenario sweeps, CSV/JSON outputs, and PNG/SVG figures. `test_model_prototype.py` checks determinism, nonnegativity, and metric bounds.

## Experiment
45 scenarios: species in {1,2,4,8,12} crossed with drought frequency {0.10,0.25,0.50}, 80 years, seed 17. Outputs are in `results/scenario_metrics.csv`, `results/timeseries.csv`, and `results/metrics.json`.

## Validation
Internal checks: deterministic replay with fixed seed, bounded traits/richness, nonnegative abundance, and extreme-frequency scenarios. External/observational validation is pending because no data rows were supplied.

## Sensitivity/robustness
The sweep compares richness and frequency. Pollution and habitat parameters are exposed in `simulate` but a full factorial sensitivity is pending; adding it requires a defined calibration/parameter range.

## Falsification
The model is falsified if observed multi-year trajectories systematically violate nonnegative dynamics, if higher diversity consistently reduces drought resilience after controlling traits, or if frequency effects reverse across replicated seeds without sampling explanation. These tests require observations.

## Reviewer risks
Uncalibrated trait distribution, arbitrary thresholds, no soil-water state, no seed bank, no spatial dispersal, and no empirical parameter uncertainty. Results should be interpreted as scenario evidence only.

## Reproducibility manifest
Run `python model_prototype.py` from the workspace. Seed=17; Python/NumPy/Matplotlib versions are recorded in `results/manifest.json`; input benchmark SHA-256 is recorded there as well. All generated artifacts remain in this workspace.

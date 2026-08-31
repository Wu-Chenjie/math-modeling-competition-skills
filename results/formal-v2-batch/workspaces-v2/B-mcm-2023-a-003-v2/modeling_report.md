# MCM 2023 A: Drought-Stricken Plant Communities

## Problem framing

The task is treated as a hypothesis-generating dynamic-system study: quantify how initial species richness, drought frequency and variability, response-trait composition, pollution, and habitat loss affect long-run community biomass, stability, and persistence. The supplied benchmark contains the official problem text but no empirical data files or rows, so the model cannot estimate real ecological thresholds.

## Data audit

The deterministic case summary reports `data_files=[]`, `data_audit=[]`, and an empty-data SHA-256. Thus there are zero observations, no units to reconcile, no missing-value pattern to estimate, and no empirical distribution to reproduce. The problem-text SHA-256 is `948959869a6e863246b0eb7c9001e82a39b9b28d8ffe881fcd8aad5bddfc9002`. All numerical parameters are declared dimensionless scenario assumptions, not measured or fitted values.

## Assumptions

Time advances in annual weather cycles with five within-year Euler steps. Annual drought is a seeded, clustered Bernoulli process; drought severity is truncated to `[0,1]`. Species differ along a drought-sensitivity trait axis. Biomass follows a nonnegative generalized Lotka-Volterra competition model. Interspecific competition is weaker than intraspecific competition, habitat loss reduces carrying capacity, pollution adds mortality, and drought exposure builds bounded adaptive memory with a maintenance cost. Closed communities have no immigration or speciation.

## Candidate models

1. Selected: stochastic-forcing generalized Lotka-Volterra dynamics with adaptive memory. It directly exposes species interactions, trait composition, environmental stress, and time trajectories.
2. Alternative: stochastic consumer-resource differential equations with explicit soil moisture. This is more mechanistic but its extra parameters cannot be identified from the supplied zero-row input.
3. Alternative: state-space statistical model fitted to plot data. It would support uncertainty-calibrated inference but is currently impossible because no observations are supplied.

## Baseline

The baseline is one species under the reference drought scenario. Richness `S=1..8` is compared using identical weather realizations (common random numbers). The operational, scenario-specific benefit threshold is the smallest `S` whose last-30-year mean biomass is at least 5% above the single-species baseline. This threshold is a model output, not a universal ecological minimum.

## Math specification

For species `i`, biomass `B_i` follows

`dB_i/dt = B_i { r(1-D_t s_i[1-0.55 a_i]) [1-(B_i+0.72 sum_{j!=i}B_j)/K] - m - 0.14 D_t s_i[1-0.55a_i] }`.

Here `K=100(1-habitat_loss)`, `m=0.16+pollution`, drought severity is `D_t`, sensitivity is `s_i`, and adaptive memory updates annually as

`a_i(t+1)=clip(a_i+0.09 D_t(1-a_i)-0.018a_i,0,1)`.

Primary responses are mean and minimum total biomass over the final 30 years, coefficient of variation, and the fraction of species with final biomass above 1.

## Code/prototype

`model_run.py` is a standard-library executable. It simulates four stress scenarios for richness 1 through 8, runs a trait-composition falsification experiment, performs local sensitivity checks, and writes JSON plus SVG. `test_model_run.py` tests determinism, state bounds, a no-drought extreme, threshold logic, and SVG generation.

## Experiment

The main factorial experiment crosses four environmental scenarios with eight richness levels under a fixed preregistered seed. The trait falsification repeats the reference scenario after replacing all response traits by the same value. Common weather sequences isolate changes caused by richness and traits from Monte Carlo noise.

## Validation

Internal validation consists of deterministic replay, bounded weather, nonnegative finite states, a zero-drought-frequency boundary test, and identical-input comparisons. Numerical outputs are generated only by the executable and stored in `results/metrics.json`. Empirical calibration, out-of-sample prediction, and claims about named plant species remain pending because the complete benchmark input supplies no observations.

## Sensitivity/robustness

The executable perturbs drought frequency and severity variability by plus/minus 20% around the reference scenario for `S=4`; percentage changes in final-period mean biomass are recorded in metrics. The four main scenarios separately expose future drought and compounded pollution/habitat stress. These are local scenario tests, not confidence intervals.

## Falsification

The response-diversity mechanism is challenged by making all species traits identical. If the apparent richness benefit is unchanged, trait complementarity is not the driver; if it weakens, the proposed mechanism survives this limited test. A stronger empirical falsification would require observed community trajectories under controlled richness and drought treatments.

## Reviewer risks

The principal risks are structural assumptions without calibration, Euler-step approximation, an imposed trait range, a single stochastic realization, arbitrary dimensionless thresholds, absence of immigration and soil-water state, and possible conclusions driven by the chosen competition coefficient. No causal, geographic, or species-specific recommendation is supported by the available input.

## Reproducibility manifest

Run `python model_run.py --years 120 --seed 2023003`, then `python -m unittest -v test_model_run.py`. Machine-readable parameters, hashes, runtime, Python version, and the unique command are in `results/repro_manifest.json`; model metrics are in `results/metrics.json`; vector figures are under `figures/`.

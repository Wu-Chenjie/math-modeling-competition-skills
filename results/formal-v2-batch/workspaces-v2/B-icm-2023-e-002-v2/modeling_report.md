# ICM 2023 E Light-Pollution Modeling Report

## Problem framing

The official task asks for a broadly applicable location-level light-pollution risk metric, demonstrations across protected, rural, suburban, and urban settings, three interventions, a two-location strategy choice, and a one-page flyer. This preregistered benchmark supplies the full problem text but no observational records. The executable work therefore verifies a general metric on a dimensionless parameter lattice; it does not claim to measure or rank any real location.

## Data audit

The deterministic case summary identifies case `icm-2023-e`, reports a verified problem source and problem SHA-256, and contains zero `data_files`, zero `data_audit` entries, zero ZIP entries, and no `rows_data`. The attachment-data SHA-256 is the empty-file hash. No binary attachment was opened. There are consequently no observed units, missing values, geographic coordinates, time periods, or sampling frame to audit. Empirical calibration, four-location application, and out-of-sample validation are pending.

## Assumptions

1. Every future indicator is normalized to `[0,1]` using a documented, location-comparable protocol.
2. Pressure has four dimensions: skyglow, trespass, glare, and clutter. Vulnerability has ecological and human-circadian dimensions.
3. Risk requires both pressure and vulnerability; vulnerability alone is not light-pollution harm.
4. Metric weights are transparent placeholders, not fitted estimates: pressure weights `(0.30,0.25,0.25,0.20)` and vulnerability weights `(0.60,0.40)`.
5. Strategy effects are hypotheses swept over parameter ranges. They are not measured causal effects.
6. Adaptive dimming can create a safety trade-off; the penalty is examined parametrically rather than asserted from unavailable data.

## Candidate models

The primary model is a pressure-vulnerability interaction metric. Its noisy-OR pressure aggregation is monotone, bounded, and allows concurrent pressure channels to compound without simple summation. A weighted additive score is retained as a transparent baseline. A calibrated spatial-statistical model would be preferred for real applications, but it cannot be estimated from the supplied input.

## Baseline

For pressure vector `p` and vulnerability vector `v`, the baseline is

`R_add = 50(mean(p) + mean(v))`.

It spans 0-100 but assigns positive risk to an unexposed yet vulnerable receptor. The executable experiment quantifies this structural contrast without treating lattice points as observations.

## Math specification

Let pressure weights `a_i >= 0`, `sum a_i = 1`, and vulnerability weights `b_j >= 0`, `sum b_j = 1`.

`P(p) = 1 - product_i (1-p_i)^(a_i)`

`V(v) = sum_j b_j v_j`

`R(p,v) = 100 P(p)V(v)`.

Thus `R` lies in `[0,100]`, is zero when all pressure channels are zero, reaches 100 only at maximal pressure and vulnerability, and is componentwise nondecreasing. Risk-level cut points are deliberately not assigned: defensible categories require outcome-linked calibration or a preregistered policy convention.

For intervention `k` with hypothetical efficacy `e`, transformed inputs are `T_k(p,v;e)`. Selection minimizes

`J_k = R(T_k(p,v;e)) + 100 lambda s e^2 I(k=adaptive dimming)`,

where `s` is normalized safety dependence and `lambda` is an explicit trade-off weight. Shielding acts on trespass and clutter, spectral control acts on ecological and circadian vulnerability to the emitted spectrum, and adaptive dimming acts on all pressure channels. These mappings are falsifiable hypotheses requiring field estimates.

## Code/prototype

`light_pollution_model.py` is a dependency-free Python CLI. Its public seam is the command-line invocation with the deterministic case-summary JSON. It rejects unexpected attached-data content, computes model and baseline summaries, checks invariants, performs sensitivity and strategy-regime experiments, writes JSON/CSV outputs, generates SVG figures, and prints a machine-readable receipt. `results/repro_manifest.json` records hashes, Python version, and the unique reproduction command.

## Experiment

The experiment exhaustively evaluates all `5^6` points formed by levels `{0,0.25,0.5,0.75,1}` across four pressures and two vulnerabilities. It computes distribution summaries for both models, centered finite-difference sensitivities, and strategy winners over a separate factorial design spanning generic pressures, vulnerabilities, efficacy, safety dependence, and penalty weight. All generated points are design points, not invented observations.

## Validation

Executable checks cover the primary metric's lower and upper boundaries, the baseline upper boundary and known unexposed-vulnerability behavior, componentwise monotonicity over every available one-step lattice perturbation, and monotone unpenalized response to increasing strategy efficacy. A nonzero exit code is returned if a check fails or nine figures are not generated.

## Sensitivity/robustness

Local partial derivatives at the normalized midpoint expose dependence on every indicator. Factorial strategy-regime counts test whether conclusions change across efficacy, safety dependence, and penalty weight. Since weights lack empirical identification, numerical rankings are scenario-conditional and must not be interpreted as location recommendations.

## Falsification

The primary metric should be rejected or revised if validated field outcomes worsen as modeled risk falls, if any normalized risk component produces a negative marginal effect absent a justified protective mechanism, if exposure-free locations show pollution-attributable effects inconsistent with measurement error, or if intervention transformations fail controlled before-after or matched-control evaluation. Strategy selection is falsified when observed post-intervention risk and safety outcomes contradict the predicted objective ordering.

## Reviewer risks

The largest risk is category error: parameter-lattice results could be mistaken for empirical location results. Other risks are uncalibrated weights, construct validity of normalization, correlated indicators, ecological and temporal scale mismatch, safety confounding, omitted spectral and weather variables, and causal claims from nonexperimental comparisons. The additive baseline is intentionally weak and is not evidence of predictive superiority. No external citations or scores are asserted because the complete benchmark input contains only the official problem text and no research corpus.

## Reproducibility manifest

Primary outputs are `results/metrics.json`, `results/grid_summary.csv`, nine files under `figures/`, and `results/repro_manifest.json`. The manifest binds the input and code by SHA-256 and records the exact command. Randomness is not used. Pending stages are empirical four-location application, calibrated selection for two locations, location-specific flyer production, and external validation; each lacks required observations or effect estimates in the benchmark input.

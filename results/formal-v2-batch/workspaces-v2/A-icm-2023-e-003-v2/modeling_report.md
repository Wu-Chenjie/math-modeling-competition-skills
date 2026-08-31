# Light Pollution Modeling Report

## Problem framing
The task requires a broadly applicable light-pollution risk metric, application to protected, rural, suburban, and urban locations, three interventions, intervention selection for two locations, and a one-page flyer. The supplied deterministic summary contains the official problem text but no location observations. This report therefore specifies and structurally tests a metric while withholding all empirical scores and rankings.

## Data audit
- Case: `icm-2023-e`; source status: `verified`.
- Data files: 0; audit entries: 0; supplied rows: 0.
- Binary attachments opened: 0. No location record can be scored.

## Assumptions
Each indicator must be normalized to [0,1] using documented, location-appropriate reference thresholds before scoring. Higher exposure and vulnerability mean higher risk. `lighting_need` is retained as an intervention feasibility constraint, not used to lower pollution harm. The 0.6/0.4 exposure-vulnerability blend is a transparent prototype parameter, not an empirically calibrated coefficient.

## Candidate models
1. Equal-weight additive baseline: simple and auditable, but fully compensatory.
2. Interaction-aware exposure-vulnerability metric (recommended prototype): prevents vulnerability from creating risk without exposure while increasing harm where vulnerable receptors coincide with exposure.
3. Multi-criteria outranking: suitable when stakeholder vetoes and non-compensatory thresholds are elicited, but impossible to calibrate from the supplied input.

## Baseline
For six normalized harm indicators, `B = 100 * mean(x_i)`. It is implemented only for complete user-supplied records; no benchmark location receives a baseline score.

## Math specification
Let `P` be the mean of skyglow, trespass, glare, and clutter; let `V` be the mean of ecological sensitivity and human vulnerability. The prototype is `R = 100 P (0.6 + 0.4 V)`. Thus `0 <= R <= 100`, `dR/dP = 100(0.6+0.4V) >= 0`, and `dR/dV = 40P >= 0`. Risk-band cutoffs remain pending calibration. Interventions accept externally justified reductions `delta_j` and update exposure as `x'_j=x_j(1-delta_j)`; the code supplies no strategy efficacy values.

## Code/prototype
`light_pollution_model.py` validates complete normalized records, computes the baseline and recommended metric, applies supplied intervention reductions, audits the deterministic summary, runs unit tests, creates metrics, and writes figures and a reproducibility manifest.

## Experiment
A 101-by-101 analytical grid checks the formula over all combinations of aggregate exposure and vulnerability in [0,1]. This is a model-response audit, not synthetic or observed location evidence. Grid points: 10201; score range: 0.0-100.0.

## Validation
The executable test suite checks bounds/monotonic direction, refusal of incomplete records, and non-increase of exposure under explicitly supplied reductions. Pressure monotonicity violations: 0; vulnerability monotonicity violations: 0.

## Sensitivity/robustness
Across the normalized domain, sensitivity to exposure lies in [60,100] score units per unit `P`, while sensitivity to vulnerability lies in [0,40] per unit `V`. Weight uncertainty, normalization thresholds, measurement error, and intervention-effect uncertainty cannot be evaluated without data and stakeholder inputs.

## Falsification
Reject or revise the prototype if calibrated indicators violate expected monotonicity, if measured post-intervention exposure increases under an intervention claimed to reduce it, if rankings are unstable under defensible normalization/weight ranges, or if out-of-sample harm outcomes are not ordered by predicted risk. None can be tested on the supplied zero-row input.

## Reviewer risks
The blend coefficient and equal within-group weights are uncalibrated; indicator definitions need operational units and sources; location sampling could be biased; correlations could be confounded; intervention benefits and safety trade-offs are not quantified; risk bands and strategy rankings would be unsupported. No literature citations are asserted because none were supplied or searched in this preregistered input.

## Reproducibility manifest
Input SHA-256: `9c136273749e640d6926cadeccad4d16dc55904d7d3a178602931f69fd4e2557`. Random seed: none (deterministic). Runtime: Python 3.12.13. Command: `python light_pollution_model.py --case-summary "C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\icm-2023-e.json"`. Pending stages: location_indicator_calibration, four_location_scoring_and_interpretation, empirical_intervention_effect_estimation, two_location_strategy_optimization, one_page_location_flyer, uncertainty_and_out_of_sample_validation, independent_domain_stage_gates.

# ICM 2023 Problem E: Light Pollution

## Problem framing
Develop a broadly applicable risk metric, apply it to protected, rural, suburban, and urban archetypes, compare interventions for two locations, and provide a promotion-flyer concept. The supplied case summary contains no observations or attachments.

## Data audit
`data_files=[]`, `data_audit=[]`, and `rows_data` are absent in the deterministic input. Therefore all component values below are transparent scenario assumptions on [0,1], not field measurements. Empirical calibration and spatial validation are pending.

## Assumptions
Components represent normalized exposure/impact dimensions: skyglow, trespass, glare, ecological sensitivity, and health/safety sensitivity. Archetype values and intervention reductions are scenario parameters, not observed values. Effects combine multiplicatively and do not include rebound.

## Candidate models
Candidate A is a weighted additive index. Candidate B is a non-compensatory maximum-component index. Candidate A is retained because its component contributions remain auditable; Candidate B is reserved for future robustness analysis. A multiplicative model is rejected because a near-zero component can mask severe risk elsewhere.

## Baseline
| Archetype | Score | Band |
|---|---:|---|
| protected_land | 27.14 | low |
| rural_community | 29.94 | low |
| suburban_community | 57.70 | moderate |
| urban_community | 81.14 | high |

These are comparative scenario outputs only. The protected archetype can retain ecological risk despite low source intensity; the urban archetype has the highest assumed multi-component burden.

## Baseline and math specification
The naive baseline is the unweighted mean. The retained metric is $R_i=100\sum_{k=1}^5 w_kx_{ik}$, with weights $(0.28,0.20,0.18,0.18,0.16)$ summing to one. Risk bands are low <33.3, moderate 33.3-66.7, high >=66.7. Intervention $j$ applies $x'_{ik}=x_{ik}(1-r_{jk})$.

## Math specification
Inputs are five dimensionless values in $[0,1]$. The score is bounded by 0 and 100 and monotone in every component for nonnegative weights. Three strategies are modeled: adaptive shielded LEDs, curfew/dimming, and zoning with dark corridors. Their actions respectively target optical spill/glare, operating duration, and ecologically sensitive space.

## Code/prototype
`run_model.py` computes baseline scores, all intervention scenarios, Dirichlet weight sensitivity, CSV/JSON outputs, and nine SVG figures. `test_run_model.py` tests the public scoring interface.

## Experiment
| Archetype | Selected scenario | Before | After | Reduction |
|---|---|---:|---:|---:|
| suburban_community | adaptive_shielded_led | 57.70 | 40.34 | 17.36 |
| urban_community | adaptive_shielded_led | 81.14 | 55.41 | 25.73 |

Selection minimizes the retained score among the three assumed interventions for suburban and urban archetypes. It is not an empirical causal-effect estimate.

## Validation
Unit tests check score bounds, monotonicity, and non-increasing interventions. Internal consistency checks show weights sum to one and all model inputs remain within $[0,1]$. External validation is pending because observations are absent.

## Sensitivity/robustness
Two thousand deterministic Dirichlet weight draws (concentration 1000 around the retained weights) generate the intervals in `results/sensitivity.json`. This tests local weight uncertainty only; structural and measurement uncertainty remain pending.

## Falsification
Collect georeferenced sky brightness, luminaire inventories, ecological response, and health/safety proxies. The metric should be rejected or revised if monotonic relations fail, intervention predictions reverse under matched controls, or out-of-sample rank agreement is no better than the unweighted baseline. Numerical rejection thresholds are pending because no calibration sample exists.

## Reviewer risks
Sampling bias, confounding between development and lighting, correlated components, subjective normalization, assumed intervention effects, and absent uncertainty from real measurements. No citations were introduced because the supplied benchmark contains none. Results must not be interpreted as measurements of specific communities. `flyer_urban_adaptive_led.md` is a communication prototype for the urban archetype, not a location-specific evidence claim.

## Reproducibility manifest
See `results/reproducibility_manifest.json` for seed, hashes, dependency versions, and command.

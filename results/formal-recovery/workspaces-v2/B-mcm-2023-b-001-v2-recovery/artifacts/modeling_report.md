# Reimagining Maasai Mara: Modeling Report

## Problem framing
The task is a policy design and comparison problem for wildlife, livelihoods, human-wildlife conflict, and implementation cost inside and around Maasai Mara. The official prompt has three requirements: recommend area-specific strategies, provide a ranking methodology with interaction/economic models, and project long-term outcomes and transferability.

## Data audit
The deterministic case summary is verified (problem SHA-256 `a22b1cdf79432f5ed5cc3443f360322e968ff4255bdabb791b5f9afae96a63f4`); `data_files` and `data_audit` are empty. No tabular observations are available, so all numeric effects below are declared scenario assumptions and not fitted estimates. Empirical calibration, causal identification, and field validation are pending.

## Assumptions
Six zones form a ring network. Candidate binary interventions are community co-management (C), zoning/corridors (Z), and a tourism levy (L). Capacity costs are 2, 3, and 1 units with a limit of 5. The network term uses mean degree and a zoning multiplier. The primary model is a normalized multi-objective maximin model across baseline, drought, and tourism-surge scenarios; a zero-action policy is the baseline. A geometric mean gives equal elasticity to wildlife, livelihood, conflict reduction, and fiscal feasibility without arbitrary additive weights. Sensitivity varies objective weights.

## Candidate models
The selected model combines a zone interaction network, constrained policy enumeration, multi-objective utility, and maximin scenario analysis. A single-weight additive MCDA baseline was rejected because the case summary identifies arbitrary weights as a common failure. An empirically calibrated spatial system-dynamics model remains pending because no observations are supplied.

## Baseline
The reference policy `000` means no incremental C, Z, or L intervention; it does not claim that current management is inactive. All comparisons are conditional changes from that reference.

## Mathematical specification
For policy x, capacity is `2C+3Z+L <= 5`. Objectives are clipped to [0,1]: wildlife and livelihood benefits, conflict reduction `1-conflict_rate`, and cost feasibility `1-cost`. Scenario score is `U_s=(W_s L_s F_s K_s)^{1/4}`; robust score is `min_s U_s`. Policies are enumerated exactly, so the capacity constraint is never relaxed.

## Code/prototype
`model.py` reads only the supplied JSON, enumerates feasible policies, evaluates all three scenarios, writes metrics, and emits at least nine PNG figures.

## Experiment
The unique command is `python model.py --case "C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\mcm-2023-b.json" --metrics artifacts/metrics.json --figures artifacts/figures --report artifacts/modeling_report.md`.

## Validation
Validation is internal consistency: deterministic reruns, objective bounds, and capacity checks. The recommended policy is `110` with robust score `0.6925`. Because there are no observations, external predictive validation is pending.

## Sensitivity/robustness
Scenario maximin ranking, computed weight sensitivity, and a directional 20-year projection are reported in the metrics file and figures.

## Falsification
The recommendation is falsified if observed wildlife, conflict, livelihood, or cost responses reverse the assumed policy directions; if zone topology differs materially; or if the capacity limit is infeasible.

## Reviewer risks
Main risks are assumption-driven effect sizes, unverified equal-importance utility, omitted stakeholder heterogeneity, and no spatial/time-series calibration.

## Long-term and transferability
The model projects directional comparisons rather than absolute population forecasts. It transfers to another preserve by replacing the zone graph, capacity costs, scenario shocks, and empirically estimated response coefficients, then rerunning the same constrained enumeration and maximin ranking.

## Reproducibility manifest
See `artifacts/manifest.json` for input hash, runtime, parameters, and output paths. No external citations or binary attachments were used.

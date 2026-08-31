# Reimagining Maasai Mara: Modeling Report

## Problem framing
The task is a policy design and comparison problem for wildlife, livelihoods, human-wildlife conflict, and implementation cost inside and around Maasai Mara. The official prompt has three requirements: recommend area-specific strategies, provide a ranking methodology with interaction/economic models, and project long-term outcomes and transferability.

## Data audit
The deterministic case summary is verified (problem SHA-256 `a22b1cdf79432f5ed5cc3443f360322e968ff4255bdabb791b5f9afae96a63f4`); `data_files` and `data_audit` are empty. No tabular observations are available, so all numeric effects below are declared scenario assumptions and not fitted estimates. Empirical calibration, causal identification, and field validation are pending.

## Assumptions and candidate models
Six zones form a ring network. Candidate binary interventions are community co-management (C), zoning/corridors (Z), and a tourism levy (L). Capacity costs are 2, 3, and 1 units with a limit of 5. The network term uses mean degree and a zoning multiplier. The primary model is a normalized multi-objective maximin model across baseline, drought, and tourism-surge scenarios; a zero-action policy is the baseline. A geometric mean gives equal elasticity to wildlife, livelihood, conflict reduction, and fiscal feasibility without arbitrary additive weights. Sensitivity varies objective weights.

## Mathematical specification
For policy x, capacity is `2C+3Z+L <= 5`. Objectives are clipped to [0,1]: wildlife and livelihood benefits, conflict reduction `1-conflict_rate`, and cost feasibility `1-cost`. Scenario score is `U_s=(W_s L_s F_s K_s)^{1/4}`; robust score is `min_s U_s`. Policies are enumerated exactly, so the capacity constraint is never relaxed.

## Code/prototype and experiment
`model.py` reads only the supplied JSON, enumerates feasible policies, evaluates all three scenarios, writes metrics, and emits nine PNG figures. The unique command is `python model.py --case case_input.json --metrics results/metrics.json --figures figures --report results/modeling_report.md`.

## Validation and robustness
Validation is internal consistency: deterministic reruns, objective bounds, and capacity checks. The recommended policy is `110` with robust score `0.6925`. Because there are no observations, external predictive validation is pending. Scenario and weight sensitivity are reported in the metrics file and figures.

## Falsification and reviewer risks
The recommendation is falsified if observed wildlife, conflict, livelihood, or cost responses reverse the assumed policy directions; if zone topology differs materially; or if the capacity limit is infeasible. Main risks are assumption-driven effect sizes, unverified equal-importance utility, omitted stakeholder heterogeneity, and no spatial/time-series calibration.

## Long-term and transferability
The model projects directional comparisons rather than absolute population forecasts. It transfers to another preserve by replacing the zone graph, capacity costs, scenario shocks, and empirically estimated response coefficients, then rerunning the same constrained enumeration and maximin ranking.

## Reproducibility manifest
See `results/manifest.json` for input hash, runtime, parameters, and output paths. No external citations or binary attachments were used.

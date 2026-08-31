# MCM 2023 Problem B: Reimagining Maasai Mara

## Problem framing
The task is to recommend spatially differentiated policies inside and outside Maasai Mara, compare wildlife, livelihood, conflict and economic outcomes, and project long-term consequences and transferability.

## Data audit
- Benchmark source: deterministic case summary `mcm-2023-b.json`.
- Official problem text: present; source status `verified`.
- Binary attachments/data files: `0` listed; none opened.
- Explicit row records available to this run: `0` (`data_audit` length `0`).
- Data hash supplied by benchmark: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Numeric calibration is therefore **pending**; no omitted rows or values are inferred.

## Assumptions
Zones, policies, stakeholders, capacities, conflict events, prices and time series must be supplied before estimation. Policy effects are treated as scenario-dependent and uncertainty is reported rather than hidden in fixed weights.

## Candidate models
1. Capacity-constrained multi-objective optimization for policy packages.
2. Animal-human interaction network coupled to an economic impact ledger.
3. Scenario-based robust dynamic projection for long-term trends.

## Baseline
A feasible baseline would be the current-boundary/current-management package, evaluated with the same objectives and capacity constraints. It is **pending_data** because no baseline measurements or policy parameters are supplied.

## Math specification
For zone `z` and policy `p`, choose binary `x[z,p]` with one package per zone. Optimize wildlife benefit, resident livelihood benefit and negative conflict subject to budget, enforcement, tourism and area capacities. Build an interaction graph from observed zone-group events; compute direct, opportunity, mitigation and spillover economic terms. Rank feasible scenarios by Pareto dominance, then an epsilon-constraint tie-break. Project state vector `s_t` under three named scenarios and report worst-case regret after calibration.

## Code/prototype
`run_model.py` validates the benchmark schema, counts only explicit rows, emits machine-readable metrics, writes this report, and creates raw/process/result status figures for q1-q3. It never fabricates observations.

## Experiment and validation
The executable experiment is a data-availability gate. Schema validation passed when this report was generated; optimization, network calibration, scenario ranking and dynamic projection are pending until row-level inputs exist. Validation targets are out-of-sample conflict/economic error, capacity-feasibility checks and scenario back-testing.

## Sensitivity/robustness
Use Pareto fronts and epsilon sweeps instead of arbitrary weighted sums; vary capacity, enforcement effectiveness and conflict elasticities over documented intervals. These sweeps are pending without parameter bounds.

## Falsification
Reject the plan if any policy package violates capacity, if observed conflict does not decrease in held-out periods, if livelihood gains rely only on an unobserved transfer, or if conclusions reverse under plausible parameter intervals.

## Reviewer risks
The principal limitation is the empty data audit. Results cannot support numerical claims, certainty estimates or policy ranking until the missing observations and units are provided. External legal and ecological claims require traceable primary citations before publication.

## Reproducibility manifest
- Input path: `C:\Users\伍辰杰\Documents\ChatGPT\mathmodel\math-modeling-competition-skills\benchmarks\case-summaries\mcm-2023-b.json`
- Input file SHA-256: recorded in `results/metrics.json`.
- Command: `python run_model.py`
- Python: `3.12.13`
- Random seed: not used (deterministic gate).
- Overall status: `pending_data`

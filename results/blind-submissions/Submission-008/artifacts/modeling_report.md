# Structured modeling report: A-mcm-2023-b-001-v2

## Problem framing
Design Maasai Mara policies balancing wildlife conservation, livelihoods, conflict reduction, and implementation cost within and outside current boundaries.

## Data audit
The deterministic summary contains official problem text only. It lists zero data files and provides no rows. No empirical calibration or observed outcome is claimed.

## Assumptions and candidate models
The normalized policy effects are explicit scenario assumptions. Candidate families are: (1) capacity-constrained multi-objective portfolio optimization, (2) stakeholder-weight Monte Carlo ranking, and (3) uncertain logistic long-term scenario projection. The baseline is the zero-intervention archetype.

## Mathematical specification
Maximize U = 0.40C + 0.35L + 0.25R - 0.25K over p >= 0, sum(p)=1, p*budget <= 1, p*C >= 0.18. Rank each strategy using w*(C,L,R,-K), where w follows Dirichlet(4,3,3,2). The long-term index is y(t) = [1 + exp(-(k(t-10)+c-0.4s))]^-1.

## Code/prototype and experiment
`model_run.py` performs an exhaustive discretized portfolio search, 20,000 stakeholder-weight draws, and 500 long-term perturbations. Machine-readable outputs are in `results/metrics.json`.

## Validation and sensitivity/robustness
The code checks feasibility directly, propagates stakeholder-weight uncertainty, and reports a 10-90% trend interval. Results are scenario diagnostics, not field estimates.

## Falsification
Reject or recalibrate the scenario if measured wildlife abundance, household outcomes, conflict incidents, visitor pressure, or costs fall outside assumed ordering or capacity. Spatial corridors and policy effects require georeferenced longitudinal data.

## Reviewer risks
Key risks are arbitrary priors and normalized effects, missing spatial network structure, unverified conservation floor, and absent empirical capacity constraints. Each remains pending rather than being filled with invented values.

## Reproducibility manifest
Run `python model_run.py` from the workspace. Seed, environment, parameters, and command are recorded in `results/reproducibility_manifest.json`; nine logical figures are emitted as PNG and SVG.

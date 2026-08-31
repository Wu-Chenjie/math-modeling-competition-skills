# Structured modeling report — Reimagining Maasai Mara

## Problem framing
Choose spatial management levers for Maasai Mara to protect wildlife/natural resources, improve local livelihoods, reduce animal–people conflict, and sustain tourism; compare policies and discuss transferability. The three requested components are represented as q1 (zoning/policy), q2 (ranking and interaction/economic methodology), and q3 (long-term scenarios/generalization).

## Data audit
The deterministic summary is verified (problem SHA-256 `a22b1cdf79432f5ed5cc3443f360322e968ff4255bdabb791b5f9afae96a63f4`) but declares no data files, no audited rows, and an empty ZIP manifest. Therefore all numerical outputs below are conditional scenarios, not measurements; empirical stages remain pending.

## Assumptions
Decision variables are normalized intensities z (protected zoning), p (community benefit/tourism management), and c (corridor enforcement), constrained by z+p+c≤1. Coefficients and objective weights are explicit priors in `results/metrics.json`; they are not observed values. The conceptual five-node network is illustrative only.

## Candidate models and baseline
- q1: multi-objective grid optimization over (z,p,c), retaining a Pareto set and a transparent weighted utility.
- q2: conceptual network analysis identifies cross-zone interfaces; outcomes use bounded response functions for wildlife, people, conflict reduction, and economy.
- q3: scenario recurrence is specified but not calibrated; baseline is (0,0,0).

## Math specification
For each feasible x, wildlife = w0+wz·z+wc·c−wp·p²; people = p0+pp·p+pc·c−pz·z; conflict reduction = 1−(h0−hz·z−hc·c+hp·p); economy = e0+ep·p+ec·c+ez·z. Utility = 0.30 wildlife + 0.25 people + 0.25 conflict reduction + 0.20 economy. Pareto dominance is componentwise over the four outcomes.

## Code/prototype and experiment
`run_model.py` executes the full scenario grid, Pareto filtering, policy comparison, report writing, nine SVG figures, tests, and manifest. The run used only the supplied JSON summary.

## Validation, sensitivity, robustness, falsification
Internal tests check feasibility, objective recomputation, Pareto non-domination, and figure count. Sensitivity is limited to one-way weight/coefficients perturbation in this preregistered no-data run; calibration, bootstrap intervals, and out-of-sample validation are pending. Falsification criteria: reject the recommended portfolio if measured wildlife, livelihood, conflict, or capacity outcomes violate the response directions or if z+p+c exceeds capacity.

## Reviewer risks
Main risks are uncalibrated coefficients, arbitrary weights, conceptual (not mapped) network edges, omitted seasonal dynamics, and inability to estimate long-term certainty. These are explicitly surfaced rather than masked.

## Reproducibility manifest
See `results/manifest.json` for input hashes, interpreter version, seed, command, and generated artifacts.

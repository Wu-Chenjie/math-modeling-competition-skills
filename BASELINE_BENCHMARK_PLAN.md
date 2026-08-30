# Baseline A/B Benchmark Plan

Status: **Protocol only; no benchmark result has been run or claimed.**

## Objective

Measure whether engineering Skill architecture improves mathematical-modeling quality, stability, validity, and cost without changing model, tools, data, time, token budget, machine, or external-search permissions.

## Groups

| Group | Configuration | Purpose |
|---|---|---|
| A | One retained math-modeling Skill (primary candidate selected after this phase) | Domain-only baseline |
| B | Same math-modeling Skill plus selected Matt Pocock engineering Skills | Architecture augmentation baseline |
| C | Reserved for later fusion Skills; not run before A/B | Post-design comparison |

The primary A candidate must be selected from the retained candidate set using documented evidence, not Stars alone. If a candidate cannot be installed or executed reproducibly, record `BLOCKED` and choose the next candidate before changing the case set.

## Case corpus

Create `benchmarks/cases/` with 6-10 historical CUMCM/MCM/ICM cases spanning prediction, evaluation, optimization, graph/network, statistics, dynamic systems/ODE, multi-objective decision, and complex data analysis. The current repository contains an eight-case `catalog_only` inventory; no catalog-only case may be scored. Before execution, each case must contain `problem/`, `data/`, `reference/`, `rubric/`, and `metadata.yaml` with `competition`, `year`, `problem_type`, `difficulty`, `expected_methods`, `common_failures`, verified source hashes, access date, and license note.

Case selection must avoid training leakage: record the source URL, access date, licensing/usage note, and whether the exact statement or reference solution appears in any Skill repository. A known overlap is either excluded or reported as a contamination risk for all groups.

## Controlled conditions

- Same model version and system-level settings.
- Same case text, attachments, reference access, Python/MATLAB/LaTeX tools, network permissions, machine, and wall-clock budget.
- Same token budget and initial context; only Skill configuration differs.
- Same stop policy and artifact directory schema.
- At least 3 independent runs per group x case with pre-registered seeds/identifiers.
- Capture prompt/config hashes, tool versions, start/end time, exit code, token usage, and all generated artifacts.

## Required workflow outputs

Every run must attempt: problem framing, data audit, assumptions, >=3 candidate models or a justified smaller set, baseline, mathematical specification, code/prototype, experiment, validation, sensitivity/robustness where applicable, falsification questions, paper-ready results, reviewer report, and reproducibility manifest. A stage may be `not_applicable` only with a reason tied to the case rubric.

## Scoring: 100 points

| Dimension | Points | Evidence |
|---|---:|---|
| Problem understanding | 10 | Objectives, evaluation object, constraints, ambiguities |
| Model reasonableness | 20 | Fit, simplicity, alternatives, no algorithm theater |
| Mathematical rigor | 10 | Symbols, dimensions, formulas, domains, constraints, derivation |
| Data handling | 8 | Missingness, outliers, leakage, scaling, quality |
| Code and solving | 10 | Execution success, real computation, stability |
| Model validation | 12 | Baseline, split/CV, residuals, sensitivity, robustness, uncertainty |
| Innovation | 8 | Useful structure/data/constraint/validation innovation |
| Result interpretation | 7 | Evidence-linked explanation and limits |
| Paper quality | 10 | Structure, logic, figures, abstract, evidence chain |
| Reproducibility | 5 | Rerunnable command, environment, inputs, outputs |

Apply hard penalties of 10-30 points for fabricated data/results, false citation, severe leakage, severe mathematical error, omitted key constraint, code failure presented as success, or paper numbers inconsistent with code. A fatal error blocks the submission regardless of the arithmetic score.

## Programmatic metrics

Implement these checks in the later `scripts/evaluate.py`: code execution success, exit code, runtime, RMSE/MAE/accuracy or case-appropriate metric, objective value, constraint violations, random-seed stability, artifact existence, figure generation, input/output hashes, and rerun equality/tolerance. LLM judges must not score values that can be computed from artifacts.

## Blind multi-judge review

Rename final packages `Submission-001`, etc. Judges do not see group labels:

- Judge A: mathematical rigor and assumptions.
- Judge B: contest modeling quality and problem fit.
- Judge C: code, experiments, and reproducibility.
- Judge D: paper structure, evidence chain, and communication.

Store each report separately, aggregate only after all reports exist, and emit `REVIEW_DISAGREEMENT` when judge scores differ by a pre-registered threshold (default: 20 points on the 100-point scale) or when fatal/major labels conflict.

## Statistics and decision rule

For each group report mean, median, standard deviation, failure rate, hallucination/fabrication rate, code success rate, reproducibility rate, token usage, runtime, and reviewer disagreement. Report case-level and pooled results with confidence intervals where sample size permits. Do not declare C superior unless it beats both A and B on pooled mean and stability while reducing fatal errors and remaining within the pre-registered cost budget. If evidence is mixed, report `INCONCLUSIVE`.

## Ablation and regression reservation

After C exists, run C Full and one removal per selected Skill (`problem-grill`, `research`, `baseline`, `adversarial-review`, `reviewer`, `sensitivity`, `robustness`, or the actual final names). Keep conditions fixed. A removal that improves quality or lowers cost is evidence to merge, narrow, or delete the Skill. Any Skill change requires a core regression subset before release.

## Reproducibility checklist

Before interpreting a result, verify: case hash, Skill commit, model identifier, initial-context hash, seed, environment/package lock, command, wall time, token count, raw outputs, generated figures, evaluator version, judge reports, and rerun status. Missing evidence is `Unverified`, never an inferred pass.

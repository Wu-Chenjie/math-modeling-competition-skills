# Math Modeling Competition Skills — Handoff Report

Date: 2026-08-31

## Scope

This repository contains the evidence-first A/B benchmark of a XiaoMa
math-modeling Skill (Group A) versus XiaoMa plus selected Matt Pocock
engineering Skills (Group B), using seven source-verified CUMCM/MCM/ICM cases.
Group C remains reserved and was not created.

## Current evidence

- 42 preregistered independent run IDs exist (7 cases × 2 groups × 3 runs).
- The corrected wall-clock budget is 7,200 seconds (120 minutes).
- Recovery/merge gate: 25 of 42 runs pass the machine artifact gate; A=12 and
  B=13.
- Four missing standalone manifests were restored only from manifests already
  embedded in valid `metrics.json` files. No numerical result was invented.
- Case-level A/B 3-of-3 coverage is not complete; MCM 2023 C has zero passing
  runs in both groups.

## Blind review

The 25 machine-scoreable runs are exposed as opaque `Submission-001` through
`Submission-025` packages. The operator mapping is isolated in
`results/blind-submissions/blind-source-map.json` and must not be shared with
judges.

Judges A, B, C, and D each produced 25 records (100 records total). Schema
validation reports zero errors. Aggregation is complete for all 25 panels;
`REVIEW_DISAGREEMENT` is emitted when the four-judge total spread exceeds the
registered 20-point threshold. No fatal flags were assigned.

## Decision

The auditable decision remains **INCONCLUSIVE**. Blind-review totals alone do
not override the preregistered requirement for three complete real runs per
group and case. Therefore no A-superior, B-superior, stability, or fusion
claim is published, and Group C remains inactive.

## Reproduction

```powershell
python -m unittest discover -s tests -v
python scripts/score_artifacts.py results/run-records-v2c results/AB-v2-recovery-merged-gate.json --merge results/run-records-v2-batch results/run-records-recovery
python scripts/prepare_blind_submissions.py results/AB-v2-recovery-merged-gate.json results/blind-submissions
python scripts/review_scores.py results/blind-submissions results/blind-submissions/judge-records results/blind-submissions/review-aggregation.json
```

## Outstanding work

Runs without complete machine evidence remain explicitly unscored. To reach a
formal superiority result, complete those runs under the 7,200-second budget,
rebuild the merged gate, repeat blind review for any newly eligible packages,
and apply the preregistered pooled-mean/stability/fatal-error decision rule.

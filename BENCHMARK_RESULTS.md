# A/B Benchmark Results (v2)

Status: **INCONCLUSIVE — real artifact runs started; no superiority claim.**

## Evidence boundary

The first 42 runner records were protocol pilots. They produced structured plans but were read-only and did not execute code, so they are retained as `pilot_unscored` and excluded from score aggregation.

The v2 protocol supplies a deterministic official-problem summary with full extracted statement text and binary-safe workbook row snapshots. Each run uses a writable isolated workspace, the bundled Python runtime, and a fixed JSON receipt.

## Real artifact runs

| Run | Group | Status | Tests | Metrics | Figures | Tokens |
|---|---|---|---:|---|---:|---:|
| A-cumcm-2022-c-001-v2 | A | completed | 2 passed | `metrics.json` | 10 | 238,589 |
| B-cumcm-2022-c-001-v2 | B | completed_with_pending | compile + run passed | `metrics.json` | 12 | 232,748 |

Both runs used the same case hashes, model, summary input, and wall-clock limit. A produced a 56-sample modeling set, LOAO/RLDA results, unknown predictions, and reproducibility artifacts. B produced 55 valid rows, type classification, subtype summaries, unknown predictions, and reproducibility artifacts. These metrics are artifact evidence, not human rubric scores.

## Full v2 run status

All 42 preregistered `-v2` IDs now have records (the two CUMCM-001 records are in `results/run-records-v2c`; the other 40 are in `results/run-records-v2-batch`). Process status is 25 completed and 17 timeout. The artifact gate passes 16 runs. Case-level pass counts are:

| Case | A pass | B pass | Gate |
|---|---:|---:|---|
| CUMCM 2022 C | 2/3 | 2/3 | not sufficient |
| ICM 2023 D | 0/3 | 2/3 | not sufficient |
| ICM 2023 E | 1/3 | 3/3 | not sufficient |
| MCM 2023 A | 0/3 | 1/3 | not sufficient |
| MCM 2023 B | 2/3 | 1/3 | not sufficient |
| MCM 2023 C | 0/3 | 0/3 | not sufficient |
| MCM 2023 Y | 0/3 | 2/3 | not sufficient |

The complete machine-readable gate is `results/AB-v2-recovery-merged-gate.json`. A runner audit found that the implementation had used a 600-second timeout although the preregistered budget was 120 minutes. The timeout was corrected to 7,200 seconds; 15 recovery runs completed under the corrected budget. Recovery records are separate and supersede only the corresponding timeout record for artifact-gate inspection; they do not increase the number of independent preregistered runs.

After recovery merge, 21/42 unique runs pass the artifact gate (A: 9/21; B: 12/21). Case-level counts remain below the required 3/3 per group for every case.

## Programmatic gate

`results/AB-v2-artifact-gate.json` confirms both runs have process success, recorded code artifacts, valid metrics JSON, figures, and a reproducibility manifest. Human dimensions and final 100-point scores remain pending blind Judges A–D.

## Findings and risks

1. The original read-only protocol was insufficient for a benchmark that scores code and solving; those records cannot be treated as quality results.
2. Writable execution is viable once the bundled dependency runtime is injected.
3. Engineering augmentation did not reduce token cost in this first pair; one A/B pair is not evidence of a stable cost difference.
4. No case meets the preregistered three-independent-real-run requirement for both groups. Blind review and cross-case aggregation therefore cannot start.

Group C, fusion architecture, ablation, and superiority claims remain prohibited until the A/B gate is complete.

## Blind-review intake (2026-08-31)

The 21 runs that pass the machine artifact gate are now copied into opaque
packages `results/blind-submissions/Submission-001` through
`Submission-021`. The operator-only mapping is kept in `blind-source-map.json`;
package manifests contain artifact hashes but no A/B group labels. Judge A–D
JSON records have a schema and validation/aggregation tool in
`scripts/review_scores.py`. No judge records have been received yet, so no
human score, pooled comparison, or superiority inference is available.

An evidence-only repair pass recovered four standalone reproducibility
manifests from manifests already embedded in `metrics.json`; no new numerical
results were created. The merged gate now has 25/42 artifact-pass runs (A 12,
B 13). Case coverage is still incomplete: no case has both A and B at 3/3,
and MCM 2023 C has zero passing runs in either group.

## Summary

This change publishes the evidence-first mathematical-modeling benchmark and its handoff materials. It records the corrected 120-minute runner, recovery gate, opaque blind submissions, four-judge intake, and reproducibility evidence.

## Cause and effect

The original benchmark records mixed pilots, timeouts, and incomplete artifacts, which made direct Skill superiority claims unsafe. The published pipeline separates pilot and real runs, resolves Windows path encoding, gates artifacts programmatically, and keeps human scoring independent from machine evidence.

## Changes

- Added source-verified CUMCM/MCM/ICM case summaries and merged A/B gate reports.
- Added blind `Submission-###` packages with operator-only source mapping.
- Added Judge A-D record generation, schema validation, disagreement detection, and aggregate output.
- Added manifest repair that only restores data already embedded in valid metrics.
- Added `docs/HANDOFF_REPORT.md` with current status and reproduction commands.

## Verification

- `python -m unittest discover -s tests -v` — 24 tests passed.
- `git diff --check` — passed.
- 42 preregistered runs retained; 25 currently pass the machine artifact gate.
- 100 blind judge records validate with zero schema errors; 25 panels aggregate.

The preregistered A/B 3-of-3 case gate is not complete, so the evidence-based decision remains `INCONCLUSIVE`; Group C is not activated.

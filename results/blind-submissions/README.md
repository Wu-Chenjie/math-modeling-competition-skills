# Blind submissions

This directory is generated from machine-scoreable runs in
`results/AB-v2-recovery-merged-gate.json`. `Submission-###` directories contain
only copied artifacts and an artifact manifest; group and case labels are kept
in `blind-source-map.json` for the operator and must not be supplied to judges.

Judge records belong in `judge-records/` and must follow
`judge-record.schema.json`. Empty or incomplete panels remain pending and do
not receive inferred scores.

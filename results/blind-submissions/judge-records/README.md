# Judge record intake

Place one JSON file per judge/submission in this directory. Use the schema in
`../judge-record.schema.json` and include all ten rubric dimensions from
`BASELINE_BENCHMARK_PLAN.md`, each within its registered maximum. Do not add
group or case labels to judge files. The aggregation script leaves incomplete
panels pending and flags score spreads above 20 points.

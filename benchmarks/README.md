# Benchmark Registry

`benchmark-config.json` fixes the comparison controls without inventing a model version or token budget. Those fields remain pending until the runtime used for the actual A/B run is selected and pinned.

The current case catalog is intentionally not score-eligible. Run:

```text
python scripts/evaluate.py eligible-cases benchmarks/cases
```

Expected current output:

```json
{"eligible": []}
```

To make a case eligible, verify the official statement/data source, add the required directories, add hashes and license notes, and change only that case's `source_status` to `verified` after review.


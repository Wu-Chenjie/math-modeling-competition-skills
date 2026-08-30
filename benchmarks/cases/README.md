# Benchmark Cases

The eight directories are a source-controlled catalog, not yet executable cases. Each `metadata.yaml` is JSON-compatible YAML so the standard-library evaluator can validate it without adding a YAML dependency.

## Ingestion gate

Before a case is runnable, add:

- `problem/` with the official statement or a license-cleared archival copy;
- `data/` with original attachments and SHA-256 manifest;
- `reference/` with independently sourced rubric/evidence, not a copied solution;
- `rubric/` with case-specific scoring notes;
- `metadata.yaml` fields `source_status: verified`, `statement_sha256`, `data_sha256`, `accessed_at`, and `license_note`.

`catalog_only` cases must be excluded from A/B score aggregation. The source repositories are discovery pointers and must not be treated as ground truth until the official statement and data are verified.

# Changelog

## Unreleased

- Added seven source-verified historical cases: CUMCM 2022 C; COMAP 2023 MCM A/B/C/Y and ICM D/E.
- Added official-source provenance, attachment hashes, PDF parse/render checks, and explicit non-official rubric boundaries.
- Pinned Group A/B Skill commits and documented the Codex CLI token-cap limitation in `docs/baseline-run-manifest.json`.
- Updated evaluator tests so catalog-only discovery cases remain excluded while verified cases are eligible.
- Benchmark scores remain intentionally unpublished until three independent A/B runs per case and blind review are complete.
- Entry smoke receipts are retained under `results/`; they are explicitly non-scoring and do not count toward the 42 required full runs.
- Added diagnostic record for A-001 runner failures; no score is inferred from incomplete or timed-out reports.
- Added deterministic full-text/data-row summaries, writable v2 workspaces, bundled dependency pinning, artifact gates, and the first real A/B artifact pair. Earlier read-only runs are explicitly marked pilot_unscored; benchmark decision remains INCONCLUSIVE.
- Completed the remaining v2 run plan: 42 records retained, 25 process completions, 17 timeouts, and 16 artifact-gate passes. Added case-level gate table; no blind review or Group C activation because the three-real-runs-per-group/case gate is unmet.
- Added `SUPERIORITY_CONCLUSION.md`; the evidence-based superiority label is explicitly `INCONCLUSIVE` until all preregistered A/B and blind-review gates pass.
- Corrected runner timeout to the preregistered 120-minute budget, completed 15 recovery runs, fixed mojibake path resolution in artifact gates, and recorded merged gate status (21/42 artifact passes; still INCONCLUSIVE).

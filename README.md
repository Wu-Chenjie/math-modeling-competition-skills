# Math Modeling Competition Skills

This repository is currently in **Phase 1: research and baseline design**.

## Phase 1 deliverables

- `CANDIDATES.md` - evidence-backed candidate inventory
- `MATT_ANALYSIS.md` - engineering Skill design analysis
- `MATH_MODELING_ANALYSIS.md` - domain workflow coverage analysis
- `GAP_ANALYSIS.md` - severity-ranked gaps and acceptance criteria
- `BASELINE_BENCHMARK_PLAN.md` - fair A/B benchmark protocol

No fusion Skills or benchmark scores are claimed in this phase. Architecture design is gated on evidence review.

## Evidence policy

Facts are marked `Observed`, interpretations `Inferred`, and missing evidence `Unverified`. GitHub popularity is a discovery signal only.

## Phase gate

Before Architecture Design, review all five documents, confirm that sources are reachable, and execute the benchmark protocol without changing conditions between groups.

## Phase 1 findings

- `Observed`: the strongest domain/process separation is in zhnnky's parser, data auditor, method selector, manifests, and G1-G6 gates.
- `Observed`: XiaoMaColtAI supplies the broadest contest-oriented role, algorithm, tool, template, and reproducibility reference set in this sample.
- `Observed`: Lupynow separates solver/paper knowledge and provides extensive cookbooks, playbooks, and Python/MATLAB templates.
- `Inferred`: Matt Pocock's highest-value contribution is Skill architecture: trigger boundaries, progressive disclosure, artifacts, human gates, and independent review. Its software `domain-modeling` must not be transplanted as mathematical modeling knowledge.
- `Rejected assumption`: Stars do not establish modeling quality; no public benchmark evidence was found in this scan.
- `Risk`: candidate repositories differ in scope (pure Skills versus full applications), so the benchmark must report product/runtime overhead separately.

The next stage is worth executing only after the five documents are reviewed because it converts these observations into an architecture proposal and a controlled Group A/B harness.

## Current execution state

The A/B harness is now scaffolded under `benchmarks/` and `scripts/`. Six unit tests cover metadata validation, catalog exclusion, hard-fail penalties, traceable run records, and summary statistics. The case registry currently has eight historical pointers but zero eligible cases because official statement/data ingestion and hash verification are still pending.

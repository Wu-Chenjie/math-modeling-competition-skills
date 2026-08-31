# Blind Review Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert artifact-gate-passing A/B runs into group-blinded submissions and provide validated Judge A–D score records plus disagreement detection without inventing scores.

**Architecture:** A deterministic Python script reads the merged gate, selects only machine-scoreable runs, copies traceable artifacts into `results/blind-submissions/Submission-###`, and writes a manifest mapping opaque IDs to source runs separately. A second script validates judge JSON records against the preregistered rubric, aggregates only complete four-judge panels, and emits `REVIEW_DISAGREEMENT` when score spread or fatal-label conflicts exceed the threshold.

**Tech Stack:** Python 3.11+, stdlib `json`, `pathlib`, `hashlib`, `shutil`, `unittest`.

---

### Task 1: Generate blinded submission packages

**Files:**
- Create: `scripts/prepare_blind_submissions.py`
- Create: `tests/test_blind_review.py`
- Create: `results/blind-submissions/README.md`

- [ ] **Step 1: Write failing tests** for deterministic numbering, group-label removal, artifact copying, and source-map separation.
- [ ] **Step 2: Run `python -m unittest tests.test_blind_review -v` and confirm failure because the generator is absent.
- [ ] **Step 3: Implement `build_blind_manifest(gate, output_root)` and CLI; copy each passing run's workspace artifacts and receipt into an opaque package, while storing group/case mapping only in `blind-source-map.json`.
- [ ] **Step 4: Re-run the focused tests and verify all pass.

### Task 2: Define Judge A–D records and aggregation

**Files:**
- Create: `scripts/review_scores.py`
- Modify: `tests/test_blind_review.py`
- Create: `results/blind-submissions/judge-record.schema.json`

- [ ] **Step 1: Add tests rejecting missing dimensions, out-of-range scores, unknown submissions, and accepting complete records.
- [ ] **Step 2: Run focused tests and observe expected failures.
- [ ] **Step 3: Implement rubric constants, `validate_judge_record`, `aggregate_panel`, and `disagreement_flags`; never fill missing scores.
- [ ] **Step 4: Re-run focused tests and verify pass.

### Task 3: Produce current artifacts and verification report

**Files:**
- Create: `results/blind-submissions/judge-records/README.md`
- Create: `results/blind-submissions/review-aggregation.json`
- Modify: `BENCHMARK_RESULTS.md`
- Modify: `SUPERIORITY_CONCLUSION.md`

- [ ] **Step 1:** Run the blind-submission generator against `results/AB-v2-recovery-merged-gate.json`.
- [ ] **Step 2:** Validate package hashes and count; create an empty aggregation with `status: pending_blind_judges` and no scores.
- [ ] **Step 3:** Run the full test suite and `git diff --check`.
- [ ] **Step 4:** Document that 21 packages are ready, judge scores remain pending, and superiority remains `INCONCLUSIVE`.

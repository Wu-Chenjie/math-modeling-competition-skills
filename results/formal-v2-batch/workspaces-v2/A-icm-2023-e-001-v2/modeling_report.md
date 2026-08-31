# ICM 2023 Problem E: Structured Modeling Report

## Problem Framing

The decision problem is to construct a transferable light-pollution risk metric, apply it to protected, rural, suburban, and urban locations, compare three interventions, select strategies for two locations, and support a one-page location-specific flyer. The metric must account for human and non-human concerns.

## Data Audit

The deterministic case summary is the complete benchmark input. It contains the verified official problem text, 0 data files, 0 audit entries, and 0 supplied rows. No binary attachment was opened. Therefore no empirical location score, category, or intervention ranking is reported.

## Assumptions

Critical assumptions are complete normalized indicators, stable indicator meaning across location types, and no imputation of missing observations. Relaxable assumptions are equal weights, quadratic aggregation (`p=2`), and explicitly uncalibrated intervention coefficients used only to test mechanics.

## Candidate Models

The implemented baseline is a transparent weighted power-mean multi-criteria model. A hierarchical spatial latent-risk model is the preferred extension once repeated spatial, temporal, exposure, ecological, health, and safety outcomes become available; it is pending because those data are absent.

## Baseline

The baseline assigns equal weight to seven dimensions: skyglow, light_trespass, over_illumination, glare, light_clutter, ecological_concern, human_concern. It produces no location outputs in this run. Risk-level category thresholds remain pending calibration.

## Math Specification

For normalized adverse indicator `z_ij` and weights `w_j`, `R_i = 100 (sum_j w_j z_ij^p)^(1/p)`, with `w_j >= 0`, `sum w_j = 1`, and `p > 0`. For strategy `k`, `z'_ij = clip(z_ij(1-e_jk),0,1)`. Bounds and effects must come from documented sources before empirical use.

## Code / Prototype

`run_model.py` is a standard-library Python implementation. It validates schema, rejects incomplete rows, computes only supported scores, runs deterministic structural experiments, and writes JSON, CSV, Markdown, SVG, and a reproducibility manifest.

## Experiment

The synthetic structural experiment ran 1000 dominance trials with seed 2023001. It observed 0 bound violations, 0 monotonicity violations, and 0 non-finite results. These are implementation checks, not empirical evidence.

## Validation

Structural validation is `complete`. Empirical validation is `pending` because the benchmark contains no observations or outcomes. Out-of-sample error, calibration, uncertainty coverage, and transferability cannot be estimated.

## Sensitivity / Robustness

On a deterministic reference vector, the risk scores for `p=1,2,4` are {"1.0": 0.5, "2.0": 0.6009252125773316, "4.0": 0.7076517579156499}. Concentrating weight 0.4 on each indicator in turn gives a score range of [0.5027701042999452, 0.7434902674398487]. These results diagnose model behavior only.

## Falsification

The implementation fails if outputs leave `[0,100]`, become non-finite, or decrease when an adverse indicator increases. Transferability fails if indicator meanings or normalization bounds differ across locations. A strategy ranking fails if it is unstable under calibrated uncertainty or violates a safety constraint. Empirical claims fail without representative observations and outcome validation.

## Reviewer Risks

- No location observations are supplied, so the official four-location application is incomplete.
- Equal weights, p=2, normalization bounds, category thresholds, and intervention effects lack calibration.
- Potential sampling bias and confounded correlations cannot be assessed without data provenance and outcomes.
- The additive separability implicit in the power mean may miss ecological-human interactions.
- Safety benefits of artificial light require explicit constraints and stakeholder evidence before intervention choice.
- SVG-only figures have not passed the pinned publication PNG/DPI visual audit because matplotlib is unavailable.
- Independent M1/P1/P2 Subagent gates were not run because the preregistered instructions did not authorize delegation.

## Reproducibility Manifest

Seed: `2023001`. Unique command and hashes are in `results/reproducibility_manifest.json`. Machine-readable report and metrics are in `results/modeling_report.json` and `results/metrics.json`. Figure provenance is in `figures/index.json`.

## Pending Stages

- four_location_empirical_scoring
- two_location_strategy_selection
- empirical_validation_and_uncertainty
- location_specific_flyer
- weight_threshold_calibration
- intervention_effect_calibration
- publication_png_figure_audit

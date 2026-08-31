# Structured modeling report

## Problem framing
Predict each listing price, quantify regional effects separately for monohulls and catamarans, and assess transfer to Hong Kong.

## Data audit
Official data hash: `17bc5eb97116d148815fd7bcc306672c967e4693cd8f5aa0368032a775c01aba`. The supplied audit contains 2346 usable monohulls and 1145 usable catamarans after excluding only header/unparseable rows. Seven supplied fields are used. No binary attachment was opened and no omitted row was imputed. No Hong Kong observations are supplied.

## Assumptions
Listing prices are positive; log errors are approximately symmetric; age is measured at the December 2020 listing date; make/variant effects are partially pooled; associations are not causal.

## Candidate models
A median-only baseline, ordinary log-linear regression, and a hierarchical make/variant log-price model were considered. The hierarchical model is selected to retain interpretability while limiting sparse-variant overfit.

## Baseline
Hull-specific global median predictors are evaluated with the same metrics as the fitted model in `results/metrics.json`.

## Math specification
For hull type t, ln(P_i)=β₀+β₁L_i+β₂A_i+β₃A_i²+β₄I(Europe)+β₅I(USA)+u_make+v_variant+ε_i, where A=2020−Year. Empirical-Bayes offsets use shrinkage denominators 10 (make) and 5 (variant). Region effect is 100(exp(β_r)−1)%.

## Code/prototype
`run_model.py` loads only JSON rows_data, cleans types, fits models, writes JSON/CSV results, and generates PNG figures.

## Experiment
Models are fit separately by hull type. Deterministic random five-fold CV (seed 2023) measures interpolation; hash-assigned variant-group CV measures performance on unseen variants.

## Validation
Report log-RMSE, USD MAE, MAPE, and log-scale R². Per-variant point and approximate 95% prediction ranges are in `results/variant_estimates.csv`. Normal-approximation region tests are descriptive because residual independence is doubtful.

## Sensitivity/robustness
Compare random-fold and grouped-variant CV, train/CV gaps, and hull-specific region effects. Large differences flag variant memorization or effect heterogeneity.

## Falsification
The model is weakened if grouped-variant R² approaches zero, regional signs reverse by hull type, or prediction intervals systematically miss. Hong Kong transfer cannot be falsified without Hong Kong listings.

## Reviewer risks
Advertised rather than sale prices, possible duplicate listings, omitted condition/equipment features, heteroskedasticity, sparse variants, nonrandom geography, and unsupported Hong Kong extrapolation.

## Reproducibility manifest
See `results/manifest.json`; unique command: `python run_model.py`.

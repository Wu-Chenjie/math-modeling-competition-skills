# Modeling report: MCM 2023 Problem Y

## Problem framing
Estimate advertised used-sailboat prices, test geographic effects for monohulls and catamarans, and identify actionable patterns for a Hong Kong broker. The permitted benchmark contains the official rows only.

## Data audit
Parsed 3491 valid data rows from the audited `rows_data`: 2346 monohulls and 1145 catamarans. Regions are {'Caribbean': 480, 'Europe': 2518, 'USA': 493}; prices span $45,000 to $2,890,000. No binary attachment was opened.

## Assumptions
Listing price is modeled as a positive noisy proxy for value; age is 2020 minus manufacture year; Europe and monohull are reference levels; rows sharing a variant are assigned to one validation fold. Missing/non-numeric rows would be skipped (none were observed).

## Candidate models
Baseline: median log price by hull type and region. Enhanced: OLS on log(price) with length, length squared, age, hull type, region indicators, hull-region interactions, and one-hot makes occurring at least 10 times.

## Baseline and math specification
For row i, `log(P_i)=X_i beta+epsilon_i`, with `X` as above. Coefficients minimize `sum_i epsilon_i^2`; prediction intervals use residual variance and the fitted covariance.

## Code/prototype
`run_model.py` loads only this JSON summary, fits the models with NumPy, writes `results/metrics.json`, `results/reproducibility_manifest.json`, and nine PNG figures.

## Experiment and validation
Five deterministic variant-group folds give baseline RMSE(log) 0.4828 and enhanced RMSE(log) 0.2373; enhanced median absolute percentage error is 0.144.

## Sensitivity/robustness
Changing the minimum make frequency from 5 to 50 leaves region log effects in `metrics.json`; the fold construction prevents identical variants crossing train/test.

## Falsification
Thirty deterministic permutations of region labels provide a null distribution; observed maximum region z is 16.73 versus null 95th percentile 2.01. This is a diagnostic, not causal proof.

## Reviewer risks
Advertised rather than transaction prices, omitted condition/features, duplicate listings, observational confounding, sparse variants, and possible heteroscedasticity. Make effects can absorb market segmentation; extrapolation beyond 36-56 ft or 2018-2020 is unsupported.

## Hong Kong stage
Pending: the permitted input contains no Hong Kong comparable listings, and no supplemental data may be invented or fetched in this preregistered run.

## Reproducibility manifest
See `results/reproducibility_manifest.json`; command: `python run_model.py`; seed: 20230830.

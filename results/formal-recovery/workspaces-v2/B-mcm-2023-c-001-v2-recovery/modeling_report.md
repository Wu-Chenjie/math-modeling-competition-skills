# Structured modeling report

## Problem framing
Analyze 2022 Wordle reported counts, hard-mode share, outcome distribution, and difficulty; forecast 2023-03-01 and classify EERIE.

## Data audit
Used only `mcm-2023-c.json` rows_data: 359 usable rows, contests 202–560, dates 2022-01-07 to 2022-12-31. Percent columns are rounded; no binary attachments opened.

## Assumptions
Contest order is the time index; log-count residuals are approximately homoscedastic for an extrapolative interval. Word attributes are limited to vowel count, unique-letter count, and repeated-letter flag.

## Candidate models and baseline
Q1 log-linear time regression; hard-mode ridge regression. Q2 ridge regressions for seven shares with nonnegative renormalization; baseline is training historical mean. Q3 tertile difficulty labels with nearest-centroid classifier.

## Math specification
For counts, ln(N_t)=β₀+β₁t+ε_t and interval exp(ŷ±1.96s). Features x=[1,t,vowels,unique,repeated]. Shares ĉ=100·max(0,xB)/Σmax(0,xB). Difficulty D=Σₖk pₖ+7p_X.

## Code/prototype
Executable: `wordle_recovery.py`; outputs `results/metrics.json` and nine PNG figures.

## Experiment and validation
Chronological 80/20 holdout avoids temporal leakage. Distribution MAE model=3.519 percentage points vs baseline=3.925; classifier accuracy=0.319.

## Sensitivity/robustness
Interval is sensitive to log-residual normality and trend extrapolation; rounded percentages and sparse word features limit calibration.

## Falsification
Model would be falsified by systematic holdout residual drift, negative/unbounded share predictions before projection, or large interval miss on future observations.

## Reviewer risks
Twitter reporters are a selected sample; no omitted rows or external word lists were used; EERIE extrapolation is uncertain.

## Reproducibility manifest
Input SHA256=22d9c6c308700c6b744d74da8c83e358eefba955f58713c65f947624cda5ac94; Python=3.12.13; command=`python wordle_recovery.py`.

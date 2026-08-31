# MCM 2023 Problem C Modeling Report

## Problem framing
The task is to model daily reported-result volume, explain hard-mode participation, predict the seven-bin score distribution for a future word/date, classify word difficulty, and identify additional data features. The benchmark is the official problem text plus the embedded audit rows only.

## Data audit
The JSON audit contains one sheet with 481 physical rows and 13 columns; 359 rows parse as dated puzzles (contest 202-560) from 2022-01-07 through 2022-12-31. Percentages are converted from percentage points to proportions and renormalized. No binary attachment was opened.

## Assumptions
1. Critical: observed Twitter reports are a time-ordered sample; future dates extrapolate the observed trend. 2. Relaxable: log-count residuals are approximately homoscedastic; checked by holdout RMSE and bootstrap-style analytic intervals. 3. Relaxable: word morphology is represented by unique/repeated/vowel/rare-letter counts. 4. Critical: reported score percentages are compositional; additive-log-ratio coordinates preserve the sum-to-one constraint. 5. Relaxable: difficulty tertiles are a useful operational label; cut points are data-derived and reported.

## Candidate models
For volume, a log-linear time/calendar regression is compared against a constant baseline. For hard mode, a weighted logit regression uses word morphology and calendar controls. For score composition, an additive-log-ratio linear model is compared with the empirical mean baseline. For difficulty, nearest-centroid classification is compared with the majority-class baseline.

## Baseline
Baselines are the training-set mean log count, mean score composition, and majority difficulty class. All reported improvements are evaluated on a chronological final 60-puzzle holdout to avoid temporal leakage.

## Math specification
Let x_t=[1,t,sin(2*pi*t/7),cos(2*pi*t/7),weekend,...]. Volume: log(N_t)=x_t beta+epsilon_t. Hard share h_t uses logit(h_t)=z_t gamma+eta_t. For composition p_t, y_tk=log(p_tk/p_tX)=w_t theta_k and p_t=softmax([y_t1..y_t6,0]). Difficulty score D_t=sum_{k=1}^6 k p_tk+7p_tX; classes are tertiles of D_t.

## Code/prototype
`run_model.py` reads only the case-summary JSON, performs all preprocessing and models, writes `results/metrics.json`, `results/daily_metrics.csv`, this report, and 12 logical figures as paired SVG/PNG files.

## Experiment
The script was run with seed 20230301. March 1, 2023 EERIE volume forecast is 9323.3 with 95% interval [5145.6, 16892.5]. EERIE predicted score distribution (1,2,3,4,5,6,X) is [np.float64(0.0), np.float64(0.0195), np.float64(0.1474), np.float64(0.3423), np.float64(0.3272), np.float64(0.1459), np.float64(0.0176)].

## Validation
Volume in-sample log RMSE=0.2974; composition final-holdout RMSE=0.0550; difficulty final-holdout accuracy=0.450.

## Sensitivity/robustness
The composition model is rerun with a 60-row temporal holdout; interval width explicitly includes forecast leverage. Morphology coefficients are interpreted directionally and should be stress-tested by dropping each feature.

## Falsification
The model would be rejected if residual variance trends strongly with time, if holdout RMSE exceeds the empirical-mean baseline, if predicted probabilities leave [0,1] or fail to sum to one, or if difficulty accuracy is below the majority baseline.

## Reviewer risks
Twitter reporters are self-selected; percentages are rounded; the word feature set omits lexical frequency and player strategy; extrapolation beyond 2022 is uncertain; no causal claim is made for word attributes.

## Reproducibility manifest
Input SHA-256: 3a6237b515ff2d07de7a07d92b2104e03a040a938783b1508e75f7700626ec01. Runtime: Python 3.12.13, NumPy 2.3.5. Unique command: `python run_model.py --case C:/Users/.../mcm-2023-c.json --out .`.

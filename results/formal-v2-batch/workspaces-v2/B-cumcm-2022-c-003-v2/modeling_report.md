# CUMCM 2022 C: 古代玻璃制品的成分分析与鉴别

## Problem framing

The four questions are treated as (Q1) descriptive weathering/type/design/color association and composition shifts, (Q2) composition-based supervised classification plus within-class subtyping, (Q3) classification of eight unknown artifacts with uncertainty/sensitivity, and (Q4) class-specific compositional association comparison. The supplied case summary is the complete input. It reports 58 Form-1 artifact records, 69 Form-2 sampling rows, and 8 Form-3 unknown rows.

## Data audit

Blank oxide cells are treated as zero because the statement defines blanks as “not detected.” For each Form-2 row, the 14 oxide percentages are summed. The preregistered validity rule is 85% <= sum <= 105%; the run found 67 valid rows and 2 invalid rows. Repeated labels such as “部位1/部位2”, “未风化点”, and “严重风化点” are grouped to the artifact identifier for validation. No omitted attachment rows were reconstructed and no binary attachment was opened.

## Assumptions

Compositions are closed data, so raw Euclidean geometry is inappropriate; centered log-ratio (CLR) coordinates are used after a 1e-4 zero replacement. Form-1 type labels are treated as reference labels, not as causal truth. Associations are descriptive; weathering mechanisms cannot be identified from these observational rows alone. Rows with invalid totals are excluded from fitted centroids but retained in the audit count.

## Candidate models and baseline

Q1 candidates were contingency-table association summaries (Cramér’s V) and type/weathering composition means. Q2/Q3 candidates were (a) CLR nearest-centroid classification and (b) a raw-percentage nearest-centroid baseline; the preregistered implementation uses CLR centroids because it respects compositional scale. Q2 subtypes use deterministic two-means clustering within each known class in CLR space. Q4 uses within-class Pearson correlations in CLR coordinates and compares correlations with Fisher-z gaps.

## Mathematical specification

For row composition x, replace zeros by epsilon and define z_i = log(x_i) - mean_j log(x_j). For class c, centroid mu_c is the componentwise mean of z among valid labeled rows. Prediction is argmin_c ||z - mu_c||_2. Grouped leave-one-artifact-out (LOAO) accuracy is the fraction correctly predicted when every row from the held-out artifact is excluded from centroid fitting. Cramér’s V is computed from the weathering-by-category contingency table. For Q4, r^c_ij = corr(z_i,z_j | class c), and the reported contrast is |atanh(r^highK_ij)-atanh(r_PbBa_ij)|.

## Code/prototype

`run_model.py` is executable from the workspace root and reads only the deterministic case-summary JSON. It writes `results/metrics.json`, `results/复现清单.json`, and 12 SVG figures (three raw/process/result views for each of Q1-Q4). `test_run_model.py` checks key counts, output coverage, manifest command, and figure count.

## Experiment and validation

The actual run produced grouped LOAO accuracy 0.9253731343283582 on 67 valid labeled sampling rows. Unknown predictions, validity sums, sensitivity labels, association tables, class-specific correlations, and the five largest Fisher-z gaps are machine-readable in `results/metrics.json`. Validation is grouped by artifact to avoid leakage from multi-point artifacts. This is an internal validation estimate, not an external benchmark score.

## Sensitivity and robustness

Unknown labels are recomputed under validity ranges 80-110, 85-105, and 90-102. The report records exact labels for each range. Additional robustness risks are zero replacement, duplicate sampling points, and the choice of two subtypes. These are exposed as parameters/metadata rather than hidden tuning.

## Falsification criteria

The classification claim would be weakened if grouped LOAO accuracy were near chance (0.5), if unknown labels changed across plausible validity ranges, or if class centroids were dominated by a single artifact. The association interpretation would be falsified by adequate replicated data showing reversal after adjustment for artifact-level clustering or measurement batch.

## Reviewer risks

The supplied audit contains sampled rows rather than the binary workbook itself; therefore row-level counts and all numerical conclusions are limited to `rows_data`. Cramér’s V does not prove causality, and LOAO is not a substitute for prospective validation. Subtype labels are algorithmic and require archaeological interpretation. Independent M1/P1/P2 gate review and publication-grade raster figure audit were not performed in this run; these remain pending stages.

## Reproducibility manifest

The manifest records the deterministic seed, input SHA-256, Python/platform metadata, and the unique command `python run_model.py`. Re-run from the workspace root, then run `python test_run_model.py`.

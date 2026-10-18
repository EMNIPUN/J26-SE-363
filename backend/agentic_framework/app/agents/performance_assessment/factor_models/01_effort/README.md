# Effort factor model

Predicts the Effort score (0-1) of one student in one sprint from commits, capped lines and files
(the proposal's five features were tested; the evidence supports three). The experiments are
notebooks, run in order. The target, success criteria and rules were fixed **before** training in
[PROTOCOL.md](PROTOCOL.md).

## Notebooks

| # | Notebook | What it does |
|---|---|---|
| 01 | `01_data_audit` | Data problems: missing and impossible values, skew, overlap, the labelled records |
| 02 | `02_splits_and_baselines` | Student-disjoint splits with leakage checks; simple baselines on validation |
| 03 | `03_preprocessing_and_features` | Feature variants and training labels, chosen on validation by a rule written first |
| 04 | `04_hyperparameter_tuning` | Ridge, Random Forest, Gradient Boosting; nested search; learning curves |
| 05 | `05_model_comparison` | Models compared without selection bias; the protocol's rule against Ridge; seeds; ablations |
| 06 | `06_error_analysis` | Residuals, subgroup errors, what the model relies on |
| 07 | `07_robustness_and_gaming` | The protocol's invariants and gaming cases |
| 07b | `07b_guard_layer` | Deterministic rules that fix the failed invariants (logged as an amendment) |
| 08 | `08_final_test` | The held-out test groups, scored once, against the protocol's criteria |

Code the notebooks share is in `training/` (`common.py` metrics and splits, `features.py` feature
variants and leak-proof training sets, `final.py` fitting and the guard layer). Results and logs are in
`training/results/` (`runs.csv` logs every result with the data hash, library versions and seed).

## Running

```
cd factor_models/01_effort
uv sync
uv run jupyter nbconvert --to notebook --execute --inplace 01_data_audit.ipynb   # then 02, 03, ...
```

Notebook 04 takes about 25 minutes; the others a few minutes each. Notebook 08 is meant to be run
once.

## Data

`dataset/effort_dataset.csv`: 144 real student-sprints (26 students, 14 teams) and 600 synthetic
records. `group` (A-E) is the split unit: teams that share a student are one group, so no student
appears in two groups. 20 real records carry the rubric score (`rater_effort`); the others have
propagated labels.

## Results

| Question | Answer |
|---|---|
| Best simple baseline | Commit count alone: validation MAE 0.053 (normalised) |
| Does tuning a model beat it? | No, once selection bias is removed (notebook 05): best tuned 0.070 |
| Complex model vs Ridge (protocol rule) | No model qualifies, so Ridge on three features |
| Invariants | The model alone fails zero-commit and spam tests; with the guard layer all pass |
| Final test (20 records, unseen students) | MAE 0.069 (95% CI 0.040-0.090), Pearson 0.93, Spearman 0.93, bias -0.010 |
| Protocol verdict | Every criterion met except **beating commit count alone** (gain -0.015, CI -0.052 to +0.011) |

## Limits

- Only 20 rated records, none above 0.75 and none with more than 19 commits.
- The ratings were made from commit evidence, so they track commit volume closely; with so few
  labels, estimating extra parameters costs more than the extra features add.
- The guard layer's setting passes at the edge of the grid searched; a lecturer should confirm the
  commit-size rules.
- More rated records, especially high-effort ones, and a rubric that separates quality from volume
  are what would let a richer model show an advantage.

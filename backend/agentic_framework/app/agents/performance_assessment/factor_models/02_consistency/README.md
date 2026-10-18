# Consistency factor model

Predicts the Consistency score (0-1) of one student in one sprint from the proposal's four features:
`AWR` (share of the 14 days with a commit), `1 - DC` (work not crowded at the deadline), `1 - LI` (no
long idle stretch) and `1 - CV` (even rhythm). The experiments are notebooks, run in order. The
criteria for the final test are in [PROTOCOL.md](PROTOCOL.md); they were written after the validation
work (notebooks 01-05) and before any test group was scored.

## Notebooks

| # | Notebook | What it does |
|---|---|---|
| 01 | `01_data_audit` | Data problems; records with no activity; the labelled records |
| 02 | `02_splits_and_baselines` | Student-disjoint splits with leakage checks; simple baselines on validation |
| 03 | `03_preprocessing_and_features` | Feature variants, training labels, and how to treat inactive students |
| 04 | `04_hyperparameter_tuning` | Ridge, Random Forest, Gradient Boosting; nested search; learning curves |
| 05 | `05_model_comparison` | Models compared without selection bias; the protocol's rule against Ridge |
| 06 | `06_final_test` | The held-out test groups, scored once, against the protocol's criteria |

Shared code is in `../ml_lib/` (splits, metrics, leak-proof feature and label builders). Results and
logs are in `training/results/` (`runs.csv` logs every result with the data hash, library versions
and seed). Data: `dataset/consistency_dataset.csv` (144 real student-sprints and 600 synthetic
records; the same five student-disjoint groups and the same 20 rated records as Effort).

## Running

```
cd factor_models/01_effort && uv sync            # the notebooks use this environment
cd ../02_consistency
../01_effort/.venv/Scripts/jupyter nbconvert --to notebook --execute --inplace 01_data_audit.ipynb   # then 02, 03, ...
```

## Results

| Question | Answer |
|---|---|
| Are all four proposal features needed? | Mostly: dropping any one costs 0.008-0.017 in error |
| Best simple rule | Active days alone: validation MAE 0.085 |
| Multi-feature Ridge | Validation MAE 0.066 (always predicting the mean: 0.195) |
| Does tuning help? | No: the tuned model (0.075) was worse than the untuned Ridge (0.066) |
| Complex model vs Ridge (protocol rule) | No forest or boosting model qualifies |
| Final test (20 records, unseen students) | MAE 0.059 (95% CI 0.039-0.073), Pearson 0.92, Spearman 0.87, rubric band exact 85% |
| Protocol verdict | Every criterion met except **beating active days alone** (gain +0.026, CI -0.011 to +0.059) |

## Limits

- Only 20 rated records, none above 0.69, rated from the same commit evidence the features use.
- The one unmet criterion needs more rated records to resolve.
- Propagated labels helped here because the label model is accurate for this factor; they did not
  help Effort or Task Complexity.

## Cleaning (what counts)

A day is active only with a counted commit; a day's size is its counted lines changed (≤800 per commit). Features: `C_AWR, C_DC, C_LI_norm, C_CV_norm, C_first_active_day, C_bimodal, C_no_activity`.

Code: [cleaning.py](cleaning.py), tests: `python -m unittest discover -s 02_consistency/tests` from `factor_models/`. How this fits the agent and the training data: [../ARCHITECTURE.md](../ARCHITECTURE.md).

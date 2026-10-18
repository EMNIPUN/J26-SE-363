# Task Complexity factor model

Predicts the Task Complexity score (0-1) of one student in one sprint from the proposal's five
features: story points (`SP`), subtask count (`SC`), files involved (`FI`), dependency reach (`DR`,
files that import the changed files, measured before the sprint) and component breadth (`CB`). The
experiments are notebooks, run in order. The criteria for the final test are in
[PROTOCOL.md](PROTOCOL.md); they were written after the validation work (notebooks 01-05) and before
any test group was scored.

## Notebooks

| # | Notebook | What it does |
|---|---|---|
| 01 | `01_data_audit` | Data problems; missing code features; the labelled records |
| 02 | `02_splits_and_baselines` | Student-disjoint splits with leakage checks; simple baselines on validation |
| 03 | `03_preprocessing_and_features` | Feature variants and training labels |
| 04 | `04_hyperparameter_tuning` | Ridge, Random Forest, Gradient Boosting; nested search; learning curves |
| 05 | `05_model_comparison` | Models compared without selection bias; the protocol's rule against Ridge |
| 06 | `06_final_test` | The held-out test groups, scored once, against the protocol's criteria |

Shared code is in `../ml_lib/`. Results and logs are in `training/results/`. Data:
`dataset/task_complexity_dataset.csv` (144 real student-sprints and 600 synthetic records; the same
groups and the same 20 rated records as Effort). 23% of real records have no linked commits, so their
`FI`, `DR` and `CB` are missing; linear models impute the training median and flag it, tree models
read the missing value directly.

## Running

```
cd factor_models/01_effort && uv sync            # the notebooks use this environment
cd ../05_task_complexity
../01_effort/.venv/Scripts/jupyter nbconvert --to notebook --execute --inplace 01_data_audit.ipynb   # then 02, 03, ...
```

## Results

| Question | Answer |
|---|---|
| Best baseline | Ridge on five features: validation MAE 0.111 (always predicting the mean: 0.128) |
| Do code features help over board features? | Yes (0.111-0.113 vs 0.129-0.130 for story points and subtasks alone) |
| Does tuning help? | No: tuned models 0.120-0.131 |
| Complex model vs Ridge (protocol rule) | No forest or boosting model qualifies |
| Final test (20 records, unseen students) | MAE 0.116 vs 0.124 for the mean (ratio 0.94), Pearson 0.08, calibration slope 0.18 |
| Protocol verdict | **Does not work**, as predicted: it misses the relative-error, correlation and calibration minimums |

## Limits

- Only 20 rated records with a narrow range (0.05-0.65, sd 0.145), so even the mean predicts well.
- `SP` and `SC` come from a reconstructed Scrum board, not from the teams.
- This is a finding about data size and label quality, not about the proposal's idea: the code features
  carry more signal than the board features, which suggests measuring complexity from the repository
  before the sprint, with far more rated records to learn it.

## Cleaning (what counts)

Counts only `code` files a task changes with a counted line (no tests, docs, config, generated, comment-only files); dependency reach on the pre-task import graph of source files, two hops, only for files that existed; story points and subtasks are the team's own.

Code: [cleaning.py](cleaning.py), tests: `python -m unittest discover -s 05_task_complexity/tests` from `factor_models/`. See [../ARCHITECTURE.md](../ARCHITECTURE.md).

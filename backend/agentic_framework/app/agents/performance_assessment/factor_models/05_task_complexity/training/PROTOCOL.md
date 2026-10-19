# Task Complexity model: protocol for the final test

**Written 2026-10-18, after the validation work (notebooks 01-05) and before any test group was
scored.** The model family and these criteria were *not* fixed before training; they were set after
seeing validation results, which showed the factor is barely learnable from this dataset. They are
fixed now, before the test.

## Task

Predict the Task Complexity score (0-1) of one student in one sprint from the proposal's five
features (`SP`, `SC`, `FI`, `DR`, `CB`). The label is `(R_avg - 1) / 4` over the five Task Complexity
criteria, available for 20 real records (the ground truth).

## Model for the final test

Ridge on the five proposal features (signed log for `FI`, `DR`, `CB`; missing values imputed with the
training median plus a flag), trained on the rated records of the four non-test groups, with `alpha`
chosen by leave-one-out on those records. Chosen in notebook 05: the untuned model (validation MAE
0.111) beat every tuned model (0.120 and above). No tuning, no propagated labels, no synthetic rows.

## Splits

The five student-disjoint groups. Each is the test group once; the model is trained on the other four.
The 20 rated records are predicted once each by a model that never saw that student.

## Success criteria

Absolute thresholds are not meaningful here (the label spread is small), so criteria are relative to
always predicting the mean.

| Criterion | Minimum (works) | Target |
|---|---|---|
| MAE as a share of always-predict-the-mean MAE | <= 0.80 | <= 0.65 |
| Beats always predicting the mean | paired group-bootstrap interval of the gain excludes 0 | and >= 20% lower MAE |
| Pearson and Spearman | both >= 0.50 | both >= 0.70 |
| Bias (mean signed error) | within +-0.05 | within +-0.03 |
| Calibration slope | 0.5 - 1.5 | 0.8 - 1.2 |
| Rubric bands (score back on 1-5) | within one for >= 85% | >= 90% within one |

On validation the model was about 13% better than the mean with a correlation of 0.23, so the
minimum is **expected to be missed**; the test is run to report that honestly.

## Sanity checks (not scored)

- The coefficients of the standardised features, per fold (story points, subtasks, files, dependency
  reach and breadth should not be negative).

## Not claimed

Anything about students outside the 0.05-0.65 label range; any claim that Task Complexity "works".

## Amendment log

| Date | Change | Reason | Post-hoc? |
| --- | --- | --- | --- |
| 2026-10-18 | Protocol written after notebooks 01-05 | The experiments were run before a protocol existed for this factor | Yes |

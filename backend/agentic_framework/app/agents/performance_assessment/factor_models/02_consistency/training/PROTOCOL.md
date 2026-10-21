# Consistency model: protocol for the final test

**Written 2026-10-18, after the validation work (notebooks 01-05) and before any test group was
scored.** Unlike the Effort protocol, the model family and these criteria were *not* fixed before
training; they were set after seeing validation results. They are fixed now, before the test.

## Task

Predict the Consistency score (0-1) of one student in one sprint from the proposal's four features
(`AWR`, `1 - DC`, `1 - LI`, `1 - CV`). The label is `(R_avg - 1) / 4` over the four Consistency
criteria, available for 20 real records (the ground truth).

## Model for the final test

Ridge on the four proposal features, trained on the rated records of the four non-test groups, with
`alpha` chosen by leave-one-out on those records. Chosen in notebook 05 because it beat every tuned
model (validation MAE 0.066 against 0.075 and above) and every single-feature rule. No tuning, no
propagated labels, no synthetic rows.

## Splits

The five student-disjoint groups. Each group is the test group once; the model is trained on the
other four. The 20 rated records are predicted once each by a model that never saw that student.

## Success criteria

| Criterion | Minimum (works) | Target |
|---|---|---|
| MAE as a share of always-predict-the-mean MAE | <= 0.50 | <= 0.35 |
| Pearson and Spearman | both >= 0.80 | Pearson >= 0.90, Spearman >= 0.85 |
| Beats active days alone (`AWR`, linear) | paired group-bootstrap interval of the gain excludes 0 | and >= 10% lower MAE |
| Bias (mean signed error) | within +-0.05 | within +-0.03 |
| Calibration slope | 0.7 - 1.3 | 0.8 - 1.2 |
| Rubric bands (score back on 1-5) | within one for >= 85% | >= 90% within one, >= 50% exact |
| MAE, students with activity | <= 0.12 | <= 0.10 |

## Sanity checks (not scored)

- Each of the four oriented features has a non-negative coefficient in every fold's model (more of any
  consistency signal never lowers the score).
- A student with no commits (features at their worst values) is predicted close to 0.

## Not claimed

Anything about students above 0.69 (no labels there); that the ratings are independent of the
features beyond what the rating form showed; any comparison to systems outside this dataset.

## Amendment log

| Date | Change | Reason | Post-hoc? |
| --- | --- | --- | --- |
| 2026-10-18 | Protocol written after notebooks 01-05 | The experiments were run before a protocol existed for this factor | Yes |

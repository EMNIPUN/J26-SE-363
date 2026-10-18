# Effort model: protocol (frozen before any model is trained)

Written 2026-10-18, before baselines or models were run. Changes after this date go in the
amendment log at the end, with the reason, and are marked as post-hoc.

## Task

Predict the Effort score (0-1) of one student in one sprint from five features
(`E_CC`, `E_LOC_net` or its capped form, `E_FC`, `E_CT`, `E_RD`). The target is the rubric score
`(R_avg - 1) / 4` over the five Effort criteria (proposal 3.1.2).

Data: `dataset/effort_dataset.csv` (144 real records, 600 synthetic). 20 real records carry the
rubric score (`label_source = rater`); these are the ground truth. The protocol does not depend on who rated.

## Splits

- Unit: the five `group`s in the dataset. Teams that share a student form one group, so no
  student appears in two groups.
- Outer loop: each group is the test group once (5 folds). Inner loop: of the other four, each is
  the validation group once and the remaining three train.
- Synthetic records join training only when **both parents** are in training groups. They are
  never in validation or test.
- Test groups are scored once, at the end, after the model and hyperparameters are fixed.
- Split files are written by `training/make_splits.py` and are not edited by hand.

## Success criteria

Headline: pooled out-of-fold predictions for the 20 rated records, each predicted by a model that
never saw that student.

| Criterion | Minimum (works) | Target |
| --- | --- | --- |
| MAE | <= 0.11 | <= 0.08 |
| Pearson and Spearman | both >= 0.80 | Pearson >= 0.90, Spearman >= 0.85 |
| Beats commit count alone | lower MAE, paired group-bootstrap interval of the difference excludes 0 | and at least 10% lower MAE |
| Bias (mean signed error) | within +-0.05 | within +-0.03 |
| Calibration slope | 0.7 - 1.3 | 0.8 - 1.2 |
| Rubric bands (score back on 1-5) | within one band for >= 85% | >= 90% within one, >= 50% exact |
| Active-only records (E_CC > 0) | MAE <= 0.12 | MAE <= 0.10 |

Missing a minimum means the model does not work. Meeting the minimum but not the target is
reported as "works, below target". The rated labels stop at 0.75, so nothing is claimed about
students above that.

## Models and the rule for keeping a complex one

Compared: mean, median, commit count alone, tasks done alone, Ridge, Random Forest, Gradient
Boosting. Hyperparameters are tuned on the inner validation group only.

Random Forest or Gradient Boosting replaces Ridge only if **all** hold:
1. Pooled out-of-fold MAE is at least 0.01 lower than Ridge's.
2. The 95% group-bootstrap interval of the MAE difference excludes 0.
3. It is better in at least 4 of the 5 outer folds.
4. It passes every invariant below that Ridge passes.

Otherwise Ridge is the model.

## Invariants (hard requirements, not scored)

- Zero commits gives a score of 0.
- Raising commits, lines or files with everything else fixed never lowers the score.
- Micro-commit spam and a library dump score at most 0.35.

A model that breaks an invariant is rejected whatever its MAE.

## Reported regardless of outcome

All models and all hyperparameter settings tried; every fold, not only the average; the metrics
where the model does badly, including active-only and per-group results; and that the labels are
the 20 rated records.

## Not claimed

Anything about students above 0.75 (no labels there); a comparison to TRACE except at system
level; that the ratings are independent of the features beyond what the form shows.

## Amendment log

| Date | Change | Reason | Post-hoc? |
| --- | --- | --- | --- |
| 2026-10-18 | Added a deterministic guard layer (zero rule, lines per commit L=100, files per commit F=20) in front of the chosen model | The chosen model failed invariants 1 and 3 in notebook 07; the protocol rejects such a model | Yes: after notebook 07, before any test group was scored |

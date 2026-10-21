# Retraining on the clean data: protocol (written before any new result)

Written 2026-10-19, before the first model was trained on `dataset/clean/`. Changes after this date go in the amendment log at
the end, with the reason, marked post-hoc.

## Why

The features were recomputed through each factor package's cleaning code (comment, blank, documentation, configuration, moved
and reformatted lines no longer count; see [ARCHITECTURE.md](ARCHITECTURE.md)). The earlier experiments on the uncleaned counts
stay as the record of the exploratory work in each factor folder. This protocol retrains Effort, Consistency and Task
Complexity on the clean data and asks the same questions.

## Data

- `dataset/clean/final_dataset_clean.csv`, extracted per factor into `<factor>/clean/dataset/` by `dataset/scripts/13_extract_clean_datasets.py`.
- 144 real student-sprints, 20 of them rated (the ground truth, unchanged). 175 simulated student-sprints (50 students),
  **training only**: never in validation or test, never scored. Their labels are estimates from the label model, never ratings.
- The 600 blended synthetic rows of the earlier experiments are not used.
- Groups A-E are the same student-disjoint groups as before. Simulated rows have no group and are in training in every fold.
- Label sources compared: rated only; rated + propagated real; rated + propagated real and simulated; propagated labels weighted
  1.0 or 0.3. Propagated labels come from a ridge model fitted on the rated records of the training groups only.

## Disclosure about the test groups

Every group was a test group once in the earlier experiments, scored on the old features with those same 20 labels. Scoring
them again is a second use of the same labels, on changed features. To keep it honest:
- every choice (variant, label source, model family, hyperparameters) is made on the **inner validation groups only**;
- the decision rules and success criteria below are the earlier protocols' own, unchanged, and are fixed now;
- the new final test is run once, with nothing tuned on it, and is reported **beside** the earlier result;
- a better number than before is not claimed as fresh evidence; it shows the effect of cleaning on the same 20 students.

## Procedure

1. Splits: outer test group (5) x inner validation group (4) = 20 combinations; the other three groups train.
2. Baselines on validation: mean, median, simple single-feature rules, Ridge on the proposal features (rated labels, penalty by
   leave-one-out).
3. Variants x label sources with Ridge, then Ridge, Random Forest and Gradient Boosting each with 11 / 30 / 30 settings
   (random search, fixed seed) for every label source. Scored on validation records that are rated.
4. Selection without bias: for each combination, a model's setting is chosen on the other three validation groups of the same outer
   fold and scored on the held-out one. These pooled predictions compare models.
5. Rule for keeping a complex model: Random Forest or Gradient Boosting replaces Ridge only if all hold: pooled MAE at least
   0.01 lower than the best Ridge; the 95% group-bootstrap interval of the MAE difference excludes 0; better in at least 4 of 5
   outer folds; it passes the invariants (Effort). Otherwise Ridge is the model.
6. Final model per outer fold: chosen setting = the simplest within one standard error of the best mean validation MAE over that
   fold's four validation groups; trained on all four non-test groups.
7. Final test, once: pooled predictions for the 20 rated records, each from a model that never saw that student, scored against
   the criteria below, with group-bootstrap 95% intervals.

## Success criteria (unchanged from the earlier protocols)

| | Effort | Consistency | Task Complexity |
|---|---|---|---|
| Error | MAE <= 0.11 (target 0.08) | MAE / mean-guess MAE <= 0.50 (0.35) | MAE / mean-guess MAE <= 0.80 (0.65) |
| Correlation | Pearson and Spearman >= 0.80 (0.90 / 0.85) | >= 0.80 (0.90 / 0.85) | >= 0.50 (0.70) |
| Beats | commit count alone (10% lower MAE at target) | active days alone (10%) | the mean (20%) |
| Bias | within +-0.05 (0.03) | same | same |
| Calibration slope | 0.7-1.3 (0.8-1.2) | same | 0.5-1.5 (0.8-1.2) |
| Rubric bands | within one >= 85% (90%, exact >= 50%) | same | within one >= 85% (90%) |
| Active-only MAE | <= 0.12 (0.10) | <= 0.12 (0.10) | not used |

"Beats" means a lower MAE whose paired group-bootstrap interval of the difference excludes 0. Missing a minimum means the model
does not work. Meeting the minimum but not the target is "works, below target".

## Effort only: invariants and the guard layer

Invariants (hard requirements): zero commits scores about 0 (at most 0.05); raising commits, lines or files with everything else
fixed never lowers the score; micro-commit spam and a library dump score at most 0.35. A model that breaks one is rejected.
The deterministic guard layer from the earlier protocol (zero rule, lines per commit 100, files per commit 20) is part of the
Effort pipeline from the start; results are reported with and without it. Guard settings are not retuned.

## Reported regardless of outcome

All models and settings tried; every fold; the metrics where a model does badly; the earlier (uncleaned) results beside the new ones;
and that the labels are the 20 rated records, rated while looking at the old counts.

## Not claimed

Anything about students above the labels' range; that simulated students prove accuracy (they carry no ratings); that the new
test result is independent of the earlier one.

## Amendment log

| Date | Change | Reason | Post-hoc? |
| --- | --- | --- | --- |
| 2026-10-19 | Second run, `clean_ref/`: labels are rubric ratings only. Statistical label propagation is removed. All 144 real records and all 175 simulated records carry a rating from `dataset/reference_ratings/` (the 20 protocol ratings are unchanged). Evaluation is pooled over all 144 real records (primary) and over the original 20 (secondary, for comparison with the first run). Label sources compared: rated only; rated + simulated own ratings at weight 0.3 and 1.0. Everything else (groups, splits, variants, models, settings, selection without bias, the rule for a complex model, criteria, Effort guard and invariants) is the protocol above, unchanged. | The first run's labels for 124 real and all simulated records were estimates from a model fitted on 20 ratings, so the models were largely learning that model. Rubric ratings give every real record a label and a much larger test set. | Yes. Written after seeing the first run's results, before any model was fitted on the new labels. The ratings themselves were written from raw evidence cards (no feature values, no model output) before this run. |

### Disclosure for the second run

- **Who rated.** All 299 new ratings, and the 20 protocol ratings, were written by the assistant against the rubric. No person rated anything. The simulated students' ratings share an author with their data. See `dataset/reference_ratings/README.md`.
- **What the result means.** Agreement between the models and these ratings shows that the models reproduce the rubric as the assistant applies it. It is not agreement with human judgement and not independent ground truth. Do not present it as human validation.
- **Targets.** The success criteria are unchanged and were not adjusted after the ratings were written. Ratings were not revised after any model result.
- **Test groups.** Every group has now been a test group twice or more on related data. The 144-record pooled test is the primary result because it has more records; the original-20 subset is reported beside it and beside the first run.


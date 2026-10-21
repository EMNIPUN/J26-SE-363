# Retrain on rubric ratings only: results (2026-10-19)

Second run of [RETRAIN_PROTOCOL.md](RETRAIN_PROTOCOL.md) (see its amendment log). Statistical label propagation is removed; every real
and simulated record has a rubric rating from `dataset/reference_ratings/`. Notebooks: `<factor>/clean_ref/RETRAIN_reference.ipynb`.

**Read this first.** All ratings (the 20 protocol ones and the 299 new ones) were written by the assistant, not by a person. The simulated
students' ratings share an author with their data. The numbers below measure how well the models reproduce the rubric as the assistant
applies it. They are not human validation and not independent ground truth. The new ratings correlate 0.93 (Effort) with the first run's
estimates for the 124 real records, so much of the "improvement" is that the labels are now more regular, not that the models learned more.

Primary test: all 144 real records, each predicted by a model that never saw that student's group. Secondary: the original 20.

| Factor | Model | 144 records | Original 20 | Beats its single-feature baseline? | Other |
|---|---|---|---|---|---|
| Effort | Ridge, 5 proposal features, guard | MAE 0.070 (target 0.08), r 0.944 / 0.927: **targets met** | MAE 0.084 (minimum met), bias +0.058 (fails ±0.05) | **No**: gain +20% but interval -0.000 to +0.048 includes 0 | **Fails the library-dump invariant** (worst fold 0.381, limit 0.35); the protocol rejects a model that breaks an invariant |
| Consistency | Ridge, 4 proposal features | MAE/mean-guess 0.39 (minimum met), r 0.876 / 0.882 (minimum met) | ratio 0.32, r 0.93 / 0.90: targets met | **No**: active days alone is as good (gain -4%, interval -0.007 to +0.003) | Active-student MAE 0.108 (minimum met) |
| Task Complexity | Random Forest, 5 proposal features | ratio 0.75 (minimum met), r 0.62 / 0.61 (minimum met), beats the mean by 25%: **works at minimum, one target met** | ratio 1.03, r 0.46 / 0.37: **fails** | Yes against the mean (interval +0.004 to +0.055) | Bias on the 20: +0.105 (fails) |

What the run does and does not show:
- Effort and Consistency meet most targets on the 144, but a single feature (commit count, active days) does about as well, so the
  multi-feature models are not shown to add value. Effort breaks one hard invariant, so it is not ready to ship as is.
- Task Complexity now clears the minimum on 144 records and rejects the "no signal" outcome of the first run, but it does not hold on
  the original 20 (small, n = 20, wide intervals) and the Random Forest was chosen under the protocol's rule (gain 0.012, interval +0.004 to +0.035, 4 of 5 folds).
- Simulated students again do not help: in all three factors "rated only" or the 0.3-weight simulated variant was best, never weight 1.0 for Effort and Consistency.
- Group A holds 71 of the 144 records; folds D and E are small, so per-fold figures are noisy.
- Test groups have now been scored on related data several times. Ratings were not changed after any model result.

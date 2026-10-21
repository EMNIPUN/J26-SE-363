# Effort: the model the agent uses

**Entry point:** [evaluate.py](evaluate.py), model card [model/effort_model.json](model/effort_model.json) (written by [../ml_lib/fit_production.py](../ml_lib/fit_production.py), evaluated without scikit-learn by [../evidence/linear_model.py](../evidence/linear_model.py)). Tests: `evidence/tests/test_linear_factors.py`.

**Model.** Ridge on four log-transformed features (commit count, net lines, files changed, tasks done; review discussions left out), after the earlier protocol's guard: a commit is credited only with the lines it carries (at most one commit per 100 lines), at most **5 files per commit** are credited, zero commits give zero.

**Evidence it works.** 144 real student-sprints, student-disjoint 5-fold cross-validation, labels = rubric ratings written by the assistant (not human ratings): MAE 0.064 (the mean predictor 0.283, commit count alone 0.087), Pearson 0.953, 98.6% within one rubric band. Gain over the commit-count baseline 0.024 MAE, 95% interval [0.008, 0.042] (grouped bootstrap over students).

**What was changed from the other branch's experiment and why.** The exp04 notebook only plots result files; its model (Ridge on the same four features) is reproduced here (MAE 0.0687 before the guard change, the notebook reports 0.0642 on its test split). Run on the earlier protocol's own invariants, that model **fails the library-dump check** (one commit with 1,000 files and 800 lines scores 0.359, limit 0.35), as did the 5-feature and 3-feature variants. Stricter file caps were added as declared candidates; caps of 10 and 5 files per commit pass all invariants (zero commits 0, spam 0.20, dump 0.305, largest drop when work increases 0.002), a cap of 3 fails one. The cap of 5 has the lowest error. It was chosen among nine candidates with the same cross-validation, so part of its edge over the 20-file guard is selection.

**Does not show.** Agreement with human graders (the labels are the assistant's, applied to evidence it could see); behaviour on languages and repositories unlike the course's; that the multi-feature model is better than commit count alone for every kind of student (it is better on average, by a margin that is small beside the label noise).

**Provisional use.** With `evidence["as_of"]` the score is computed on counts to date, flagged provisional, and its interval widens with the share of the sprint still to come. Needs at least one day of the sprint.

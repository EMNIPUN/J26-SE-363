# Collaboration: protocol (written before any combined model or score was built)

Written 2026-10-19. Changes after results are seen go in the amendment log at the end, marked post-hoc. The comment-substance scorer has its own protocol:
[SUBSTANCE_PROTOCOL.md](SUBSTANCE_PROTOCOL.md).

## Why the combining step is fixed-weight, not learned

The proposal (section 3.1.5) learns an intercept and six weights from human collaboration ratings. The data cannot support that here:

- Only 13 of the 144 real student-sprints contain any review or comment (12 reviews from 4 reviewers, 1 other comment); the other 131 sit at "no review".
- The only collaboration ratings are the assistant's (see `dataset/reference_ratings/README.md`), not independent human ratings. The four criteria follow the same few signals, so they add no independent information.
- The 50 simulated students and their reviews were written by the assistant; they can exercise the pipeline, not measure accuracy.
- No public dataset has student-level collaboration ratings.

A learned combiner would learn "no reviews means low" and would look better than it is. The combiner is therefore **specified, not fitted**, and the learned version is kept only as a labeled pipeline test.

## The score

Six measures, each scaled to 0-1, combined with equal weights (the least arbitrary choice when nothing can be fitted):

**Collaboration = mean of: review comment substantiveness, issue comment substantiveness, meaningful mentions and replies, reviewed pull requests, authored comments, interaction response and resolution rate.**

| Measure | Definition | Scaling (design constant, not fitted) |
|---|---|---|
| Review comment substantiveness | mean score of the student's reviews on other people's pull requests, from the comment-substance scorer after the guard layer | already 0-1 |
| Issue comment substantiveness | same, for discussion comments | already 0-1 |
| Meaningful mentions and replies | replies to teammates plus mentions that count | min(1, count / 3) |
| Reviewed pull requests | distinct other-people pull requests reviewed or commented on, plus merged for others | min(1, count / 3) |
| Authored comments | reviews and comments with text, after the guard layer (approvals and one-word texts do not count) | min(1, count / 5) |
| Interaction response and resolution rate | share of the student's own pull requests resolved (merged or closed) | already 0-1; defined only when the student opened pull requests |

A measure with no evidence (for example no own pull requests) is left out of the mean instead of counted as 0.

**Evidence gate.** If the team had no review activity at all in the sprint (nobody reviewed anything), the score is **not available** with a warning, not 0: a student must not be marked down for something the team never did. Fusion treats a missing Collaboration score as missing, not low.

The scaling constants (3, 3, 5) and equal weights are **design assumptions**, stated as such in the thesis. Their effect is measured (sensitivity below), not tuned.

## What is tested, and what is not claimed

1. **Invariants** (must hold; a failure is a bug): no activity gives 0 or "not available" by the gate; raising the number of substantive reviews never lowers the score; adding any number of approvals, one-word texts, quoted or padded comments, or comments on one's own pull request does not raise it; a bot account does not count.
2. **Sensitivity to the design assumptions.** Score every student-sprint under 1,000 random weightings (Dirichlet, equal on average) and under caps scaled by 0.5x and 2x. Report the Spearman correlation of each variant with the default ranking. Target: median >= 0.90; minimum: >= 0.80. Real and simulated students are reported separately.
3. **Pipeline test of a learned combiner** (notebook 03): Ridge, Random Forest and Gradient Boosting on the six measures against the assistant's four-criterion ratings, grouped by student, with baselines (review count alone, the mean). It runs on the simulated students only for the conclusion; the real-student figures are shown but marked as limited evidence. Its purpose is to show the learned combiner is not better than the fixed one by a margin that justifies it; it does not validate Collaboration.
4. **Real-student report** (data audit): how many student-sprints and teams have any signal, and the score distribution; reported as limited evidence.

**Not claimed:** that Collaboration is accurate for real students; that equal weights are right; that the substance scorer (trained on professional OpenStack reviews) transfers to student comments. Validation against human collaboration ratings is future work and needs ratings of students from teams that review each other.

## Notebooks (`training/experiments/`)

| Notebook | Content |
|---|---|
| `exp01_dataset_analysis/00_DATASET_ANALYSIS.ipynb` | why the CRScore human-rated data was rejected for a text-only scorer (record of the analysis; its data is not kept) |
| `exp02_substance_scorer/01_DATA_AND_BASELINES.ipynb` | public data (OpenDev, RevHelper), cleaning, guard layer, baselines for the substance scorer |
| `exp02_substance_scorer/02_ENCODER_TUNING.ipynb` | encoders and heads, tuning without selection bias, external test |
| `exp02_substance_scorer/03_COLLABORATION_SCORE.ipynb` | the scorer on student texts; learned combiner as a pipeline test |
| `exp03_fixed_score/04_FIXED_SCORE_AND_SENSITIVITY.ipynb` | the specified score (`score.py`), data audit, sensitivity to weights and caps, behaviour-class face check, invariants |

The public data is downloaded on demand by `helpers/download_data.py` into `dataset/raw/` (not committed). Each experiment folder keeps its own `results/` (the trained scorer is in `exp02_substance_scorer/results/`); shared code is in `helpers/`.

## Amendment log

| Date | Change | Reason | Post-hoc? |
| --- | --- | --- | --- |
| 2026-10-19 | Decision after the substance-scorer runs: the scorer trained on OpenDev (RoBERTa embeddings, logistic head) is kept as it is and presented as an estimate of "likely to be acted on" with its limits stated (AUC 0.70 within OpenDev, 0.56 on RevHelper, 0.16 Spearman against human relevance ratings of human-written comments, no validation on student comments). The rule-based score in `cleaning.py` stays the default for the substance measures. | Four public datasets were tried (OpenDev/RevHelper, CuRev, CRScore, GitHub-codereview); none gave a text-only scorer that works on human comments. | Yes. |
| 2026-10-19 | `score.py` counts a pull request as reviewed, and a mention/reply or a text as an authored comment, only when the text has substance above 0 (approvals, one-word texts and padding no longer count). | The first test run showed padded comments on extra pull requests raised the score, violating invariant 1. | Yes (found by the invariant test, before the audit). |
| 2026-10-19 | Result of the audit and sensitivity run, **no change made**: 136 of 144 real student-sprints are not scored (no team review); 75 of 128 scored simulated sprints tie at 0.25 because the response/resolution measure credits merging one's own pull requests; the sensitivity target (min Spearman >= 0.80) is met for caps but not for random weightings (min 0.08-0.14, median >= 0.995). Recommended amendment, not applied: define the response/resolution measure from other people's reviews and comments on the student's own pull requests (needs per-pull-request counts in the evidence). | Reported as found; changing the definition after seeing the data would be post-hoc. | n/a |

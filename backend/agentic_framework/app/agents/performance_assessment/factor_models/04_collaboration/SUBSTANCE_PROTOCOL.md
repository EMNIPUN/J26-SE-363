# Collaboration, step 1: protocol for the comment-substance scorer (written before any model was trained)

Written 2026-10-19. Changes after the first model is trained go in the amendment log at the end, with the reason, marked post-hoc.

## What is trained, and why on public data

The proposal (section 3.1.5) scores how substantive a review comment is (0-1) with a frozen pretrained sentence encoder and a lightweight
regression head. That score becomes `Co_PRC_depth` / `Co_IC_depth`. The student data cannot train it: the real students wrote 12 reviews and 1
comment, none longer than 10 words. The head is therefore trained on public labeled review comments; student texts are only scored.

This is **transfer learning by feature extraction**: the encoder is pretrained on general text and kept frozen; only the head learns from our labels.
Fine-tuning the encoder is not in the proposal and is an optional last experiment (see below).

## Data

| Set | Content | Size | License | Use |
|---|---|---|---|---|
| OpenDev (WSU-SEAL/CR-usefulness-EMSE) | manually annotated OpenStack Nova review comments, `is_useful` | 2,500 (2,052 useful) | GPL-3.0 | training, tuning and grouped cross-validation |
| RevHelper (masud-technope/RevHelper-Replication-Package-MSR2017) | OpenStack Nova comments, useful / not useful | 1,480; 1,464 after removing 16 texts also in OpenDev | MIT | **external test**, never used to choose anything |
| Student texts | reviews and comments in the real student repositories (13) and the simulated students' (140) | 153 | - | scored only; no labels |

Raw data is downloaded by `download_data.py` into `data/raw/` and is **not committed**. Label meaning: a comment is "useful" when the code author acted on it. That is related
to, not the same as, "substantive", and it depends on the code the comment was about, which the text does not contain.

## Pipeline

1. Clean the text with `cleaning.clean_text` (the function applied to student comments in production).
2. Guard layer (the rule part of `cleaning.substance`): approval-only text ("LGTM", "ok", "👍"), fewer than 3 words after cleaning, and padding score 0 and are not sent to the model.
3. Embed with a frozen encoder; train the head; output a probability in [0, 1] as the substance score.

## Procedure

1. **Splits.** Within OpenDev, five outer folds grouped by code change (`change_id`), four inner folds inside each outer training set; comments of one change are never in two roles.
2. **Baselines**, same folds: constant; comment length (log words) with logistic regression; the rule score of `cleaning.py`; TF-IDF (1-2 grams) with logistic regression.
3. **Encoders** (frozen): `all-MiniLM-L6-v2`, `all-mpnet-base-v2`, `roberta-base` (mean pooling). Embeddings are computed once per encoder and cached.
4. **Tuned**: encoder; text variant (embedding only, or embedding plus length, a code-present flag and a question flag); head family and its settings: logistic regression (penalty C on a log grid, 9 values), Random Forest (12 random settings), Gradient Boosting (12 random settings), fixed seed.
5. **Selection without bias.** Every configuration is scored on every (outer, inner) combination; the configuration for a combination is chosen on the other three inner folds of the same outer fold and scored on the held-out one. These pooled predictions compare families and encoders.
6. **Rule for keeping a complex head.** Random Forest or Gradient Boosting replaces the best logistic head only if all hold: pooled AUC at least 0.01 higher; the 95% group-bootstrap interval of the AUC difference excludes 0; better in at least 4 of 5 outer folds. Otherwise logistic regression is the head.
7. **Final configuration**: the simplest within one standard error of the best mean inner AUC, trained on all of OpenDev.
8. **External test, once**: the final configuration trained on OpenDev, scored on RevHelper; the reverse direction (RevHelper to OpenDev, same configuration) is reported beside it. Nothing is tuned on either.
9. **Optional last experiment**: fine-tune the best encoder end to end (CPU, small). Kept only if it beats the frozen version on the same protocol by the rule in step 6.

## Success criteria (fixed now)

Stated against the public labels, because there is no student ground truth.

| | Minimum (works) | Target |
|---|---|---|
| External AUC, OpenDev to RevHelper | >= 0.70 | >= 0.75 |
| Grouped cross-validation AUC within OpenDev | >= 0.70 | >= 0.75 |
| Beats TF-IDF + logistic (pooled AUC difference, paired group-bootstrap interval excludes 0) | yes | gain >= 0.03 |
| Guard layer: approval-only and one-word texts score 0 | all | all |
| Brier score reported | - | - |

Missing a minimum means the encoder-based scorer is not shown to work; the rule-based score in `cleaning.py` stays as the stand-in.

## Reported regardless of outcome

All encoders, heads and settings tried; every fold; the baselines; the cross-direction result; the student-text scores and what they do and do not show.

## Not claimed

That the scorer measures collaboration among students; that its accuracy on student comments is known (no human labels exist for them); that
agreement with the public labels carries over to a different population. The student-text section of the notebook is a sanity check only. The simulated reviews were
written by the assistant and only exercise the pipeline.

## Amendment log

| Date | Change | Reason | Post-hoc? |
| --- | --- | --- | --- |

## Run 2: is a context-aware relevance rating achievable? (written before the test)

Datasets tried after the first run (see `training/reading_0.md`): CuRev (model-written comments and model-written scores, unusable), the CRScore human study (reliable human ratings, but 90% model-written
comments, and relevance is judged against the code), and `ronantakizawa/github-codereview` (real comments, but its `quality_score` is a length-driven rule, not a rating).

**Question.** If the judge can see the code change, how well can relevance be predicted for **human-written** review comments? Test: a language model (`openai/gpt-oss-120b` via Groq, temperature 0, public data only)
rates relevance 1-5 for the 290 human-written comments of the CRScore study (`system == msg`), in two variants on the same comments: **with** the code change and **without** it (comment only).
Reference: the human relevance rating. Nothing is tuned on these 290 comments; the prompt is fixed below before the run.

**Criteria (fixed now).** Spearman correlation with the human relevance, student-independent bootstrap by diff for the 95% interval. Context is worth pursuing if the **with-code** variant reaches Spearman >= 0.50 and beats the
**comment-only** variant with a paired interval that excludes 0. If the with-code variant is below 0.30 the labels are too hard to predict at this size and fine-tuning a cross-encoder is not justified on this data.
Reference points already measured on these comments: comment length alone 0.14; text models trained on this data 0.06 to 0.14; human-to-human agreement ICC 0.80 (a ceiling near 0.9).

**Limits.** One rater per comment for most of the 290; the model may have seen CodeReviewer data in pre-training; public code only, never student code. The result bounds what is possible with a prompted model; it does not train anything.
| 2026-10-19 | "Run 2" (the context-aware relevance test with a language model) was **not run**: the owner stopped it, and the data used by the later experiments was deleted. A blind rating of 100 human-written CRScore comments by the assistant agreed poorly with the human ratings (Spearman 0.23, bias +1.5), so assistant ratings were not used as labels. | Nothing from Run 2 was used for any result. | Yes. |


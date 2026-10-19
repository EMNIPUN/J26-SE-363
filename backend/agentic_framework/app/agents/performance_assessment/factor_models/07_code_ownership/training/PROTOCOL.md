# Code Ownership: protocol (written before any model was fitted)

Written 2026-10-19. Changes after results are seen go in the amendment log at the end, marked post-hoc.

## What is built (proposal 3.1.8)

KO = (R - 1) / 4, where R is the 1-5 comprehension rating predicted from a student's answer to a question about their own code. The pipeline is: choose the student's
code (Effort's counted lines) -> generate a question from the syntax tree -> the student answers -> a frozen code-text encoder plus a lightweight regression head
rates the answer using the question, the code and a reference explanation. Only the last step is learned; everything before it is deterministic code in the root of
this folder (`cleaning.py`, `questions.py`, `quiz.py`).

## Data (and what it cannot show)

`dataset/ownership_qa.csv`: 36 real Python standard-library functions (public, PSF licence, no student code), one generated question each, 216 answers.
Every answer was **written by the assistant (Claude) at a target rubric level 1-5; none comes from a real student and no human rated any of it.** No language-model
API was used. An independent rating by a separate Claude instance that saw only a shuffled sheet (no levels) is added as a second opinion
(`rating_independent`). Consequences stated up front:

- Results measure whether the pipeline separates answers written at different levels of understanding, in the assistant's writing style. They do **not** measure
  agreement with human graders on real student answers. The proposal's human-rated validation (Pearson/Spearman/MAE/RMSE, ICC between raters) is still to be done
  with real answers (future work, needs the live quiz).
- 36 functions are few; confidence intervals are wide and are reported.

**Label.** Primary label: the written level (1-5). The independent rating is reported as agreement (QWK, Spearman, exact and within-one) and as a sensitivity label
(mean of the two) in the final test. If the two raters agree poorly (QWK < 0.60) the primary label is not changed, but the result is reported as limited.

## Splits (fixed now)

- Unit of grouping: the function (all answers to one function stay together; no function appears in two roles).
- Final test: 6 functions, one per question type, chosen by hash order (`sha256(snippet_id + "final-test")`, lowest within each type). Scored once, after the choice.
- Development: the other 30 functions, 5 folds grouped by function (stratified by question type); tuning uses 4 inner folds inside each outer training set, so
  the tuned score is never from data used to choose the setting (no selection bias).

## What is compared (all fixed now)

Baselines: training mean; answer length; identifier recall (share of the code's identifiers the answer mentions); reference-fact overlap (rule: share of the facts'
key terms in the answer); TF-IDF similarity of answer to reference text; ridge on these hand-built features.

Encoders (frozen, mean-pooled): UniXcoder-base, CodeBERT-base (the proposal's choices), all-mpnet-base-v2 (general text, as a control). CodeT5+ is not used: its
loader runs downloaded code (`trust_remote_code`), which is not accepted here.

Inputs to the head (feature sets): A answer only; B answer + similarity to reference/code/question; C B + the answer-times-reference interaction; D the joint embedding of
"question + answer"; each with and without the hand-built features.

Heads: ridge, SVR (RBF), kernel ridge, random forest, gradient boosting, small MLP; each with a grid fixed in the notebook before the run.

**Rule for keeping a complex head:** a head more complex than ridge is kept only if it beats the best ridge by a paired grouped-bootstrap interval that excludes 0
on the development folds AND wins in at least 4 of 5 folds; otherwise ridge is used.

**Metrics:** Spearman and Pearson (rating vs prediction), MAE and RMSE on the 1-5 scale, QWK on rounded predictions, ICC(2,1) against the label, all with grouped
bootstrap intervals (resampling functions). The proposal's reference point is 0.80-0.81 correlation of a fine-tuned encoder with human graders (Oli et al.); it is quoted
for context, not as a target we can claim on this data.

## Guards (deterministic, before the model)

An answer is rated 1 without the model when: it is empty or has fewer than 4 words; it is (almost) a copy of the question; or most of its text is lines copied from the
code (>= 60% of its words in a code line). These are tested in notebook 03 by adversarial answers (code paste, question echo, generic filler, an answer for a different
function, padding with repeated words). **Pass criteria (fixed now):** the median predicted rating of each attack set is at most 2.0, and the median of the "answer of a
different function" set is at most 2.0 (a scorer that rates a fluent answer to the wrong code highly is not checking understanding).

## Production decisions fixed now

- The score is not available (the factor is dropped and the weight redistributed, not scored 0) when there is no quiz answer yet, when the encoder cannot be loaded, or
  when the code is not Python and so no structural question could be generated and the scorer's domain does not cover it (the result then carries a warning instead of
  a score). The 48-hour window, the extension cap of 0.50 and the double-timeout zero stay in the agent's quiz node (`com_agent/config/quiz_timeout_settings.yaml`).
- The passive features (survival, primary-owner share) are reported as context for the instructor and are not part of KO, as in the proposal.

## Amendment log

| Date | Change | Reason | Post-hoc? |
| --- | --- | --- | --- |
| 2026-10-19 | 36 extra answers (short correct, long weak) added to `answers_extra.txt` before any model was fitted. | First pass: answer length predicted the written level with Spearman 0.83, so a length rule would have looked like understanding. After the addition: 0.50. | No (before modelling). |
| 2026-10-19 | Added two hand-built features, `focus_overlap` (share of the terms of the fact the question asks about that the answer uses) and `exc_named` (the exception named in that fact appears in the answer); features version ko_features/2. All encoders re-run with them. | First development results (mpnet only, features version 1): every embedding model scored about the same as answer length (Spearman about 0.5), so the hand-built features needed to look at the asked-about fact, not at all facts. | **Yes**: made after seeing mpnet development results, before UniXcoder/CodeBERT results and before the final test set was opened. |
| 2026-10-19 | Added the production rule: the encoder model is used only if its paired grouped-bootstrap MAE difference to the best hand-built-feature ridge has a 95% interval excluding 0 in its favour; otherwise production uses the hand-feature head and the encoder is reported as not helping. | The proposal wants an encoder, but a model that does not beat simple features should not carry a heavy dependency (torch, 500 MB weights) into the agent. | **Yes**: same point in time as above. |
| 2026-10-19 | CodeT5+ and CodeBERT: see the final comparison for which encoders were run (downloads from the hub were slow; any encoder not run is listed there). | Practical. | Yes. |
| 2026-10-19 | The hand-built block of a "+H" feature set is now weighted (`hw` in 1, 5, 20, chosen by the inner folds for ridge, SVR and kernel ridge) and the embedding block alone is compressed (PCA) for the forest, boosting and MLP heads (`ko_blocks.py`). All encoders re-run. | After the version-2 features, mpnet+H ridge (MAE 0.275) was worse than the same hand-built features alone (0.215): 12 columns drowned by 768 embedding columns. The first version of the protocol did not foresee that block structure. | **Yes**: made after seeing mpnet development results, before the final test set was opened. |

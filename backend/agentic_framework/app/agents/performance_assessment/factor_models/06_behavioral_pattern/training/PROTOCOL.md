# Behavioral Pattern: protocol (written before any rule was evaluated on data)

Written 2026-10-19. Changes after results are seen go in the amendment log at the end, marked post-hoc.

## What is built (proposal 3.1.7)

A **rule-based classifier**, not a trained model. For one student in one sprint it reads the Effort (E), Consistency (C) and Collaboration (Co) scores and the Consistency
package's `C_bimodal` flag, decides which of five contributor patterns fits (or none), and returns a score modifier that the fusion step multiplies onto the final score:
`S = BP_modifier * (w1*E + w2*C + ...)`. The Code Ownership and Requirement Fulfillment scores are not used by any of the five rules (the proposal mentions them as
context only).

## The rules (the proposal's conditions; thresholds named so they can be calibrated)

| Pattern | Condition | Modifier range (weak evidence -> strong evidence) |
|---|---|---|
| Consistent deep contributor | E > E_high and C > C_high | 1.10 -> 1.20 |
| Last-minute rusher | E > E_high and C < C_low | 0.95 -> 0.90 |
| Reviewer or coordinator | E < E_mid and Co > Co_high | 1.00 -> 1.05 |
| Burst worker | E > E_high and `C_bimodal` = 1 | 1.00 -> 0.95 |
| Free rider | E < E_low and Co < Co_low | 0.85 -> 0.80 |
| (none of the above) Balanced contributor | - | 1.00 |

Proposal thresholds: E_high = C_high = Co_high = 0.7, C_low = Co_low = E_low = 0.3, E_mid = 0.4.

## Decisions fixed now

1. **Fixed numbers, not percentiles of a group.** The agent scores one student at a time, so thresholds are numbers stored with the rule set (`thresholds.json`, with the
   cohort and date they came from), never computed from the students being scored.
2. **Two threshold sets are evaluated and reported side by side:** `proposal` (the numbers above) and `calibrated`. Calibrated means the proposal's cut points read as cohort
   quantiles: 0.7 -> the 70th percentile, 0.3 -> the 30th, 0.4 -> the 40th percentile of the training cohort. E and C: the 144 real student-sprints. Co: only the sprints where
   Collaboration is available, real and simulated together (the real students alone give 8). This mapping is fixed here; nothing is tuned on agreement.
3. **Overlap.** Last-minute rusher and Burst worker can both match (same Effort condition, low Consistency and bimodal activity). When more than one pattern matches the one
   with the **milder modifier wins** (benefit of the doubt: Burst worker over Last-minute rusher). All other pairs cannot match together (their Effort or Consistency/
   Collaboration conditions exclude each other); a test checks this over a grid.
4. **Modifier inside the range.** `strength` in 0..1 is the smallest margin among the pattern's conditions, each margin being the distance past the threshold divided by the
   room left up to the end of the scale. `modifier = weak + (strong - weak) * strength`. The result is always inside the pattern's range and the whole system is capped to
   0.80-1.20. `strength < 0.10` is flagged "near a threshold".
5. **Missing inputs.** A required score (E, or C) that is missing or outside 0-1 makes the pattern **not classifiable**: pattern "Unclassified", modifier 1.00, warning (no
   penalty, no reward). **Collaboration unavailable** (the Collaboration factor reports "not available" when nobody in the team reviewed or commented in the sprint): the
   two rules that need it (Reviewer or coordinator, Free rider) cannot fire; the other three still can; the result says which rules could not be tested. A missing score is never
   replaced by 0 or by a typical value. `C_bimodal` missing means the Burst rule cannot fire.
6. **No other factor feeds the rules.** If Effort or Consistency came from the agent's fallback (not computed), the agent passes them as missing.

## What is evaluated (and what it can and cannot show)

There is no trained model, hence no test set in the usual sense. The proposal's validation, agreement with independent instructor judgements, needs instructors and is not
possible yet; the form for it is prepared (`dataset/INSTRUCTOR_FORM.md`). Until then:

1. **Firing audit.** For both threshold sets: how often each pattern fires on the 144 real and 175 simulated student-sprints. A rule that never fires is reported as untestable here.
2. **Agreement with assistant labels, as a pipeline check only.** (a) The 6 behaviour classes the simulated students were written to follow; (b) the pattern the assistant gave
   the 20 real anchor records (`GT_BP_pattern`, one rater). Both come from the same kind of reasoning as the rules, so agreement shows the rules implement the
   idea, not that they match instructors. Accuracy, Cohen's kappa, per-pattern recall/precision and the confusion matrix; the same table for the proposal thresholds.
3. **Sensitivity.** Thresholds shifted by -0.10, -0.05, +0.05, +0.10 (all together): share of student-sprints whose pattern changes. Target fixed now: at most 15% change for
   a shift of 0.05.
4. **Effect of the modifier.** Spearman between the final score with and without the modifier (target at least 0.95: the modifier must adjust, not reorder, the cohort) and the
   largest change of a single student's score.
5. **Invariants (unit tests, must hold).** Modifier always inside the pattern's range and in 0.80-1.20; no pattern when an input is missing; monotonic strength; at most one
   pattern; Collaboration missing never produces Free rider or Reviewer; deterministic.

## Honest limits stated up front

- Collaboration is "not available" for most real sprints (136 of 144), so on real data the Free rider and Reviewer rules are mostly untestable.
- The Effort and Consistency scores used for calibration are the marks in `dataset/clean/final_dataset_clean.csv`, produced by models fitted on 20 anchor ratings by a single
  assistant rater; they inherit that limit.
- All labels used in the agreement check are assistant-written.

## Amendment log

| Date | Change | Reason | Post-hoc? |
| --- | --- | --- | --- |
| 2026-10-19 | Collaboration keeps the proposal's absolute cut points (0.7 / 0.3) in the calibrated set; only Effort and Consistency use the quantile reading. | The quantile reading gave Co_high = Co_low = 0.25 (77 of the 133 available scores tie at 0.25 because the response-rate measure of the Collaboration score gives that value to anyone who only merged their own pull requests), which makes the Reviewer and Free-rider rules meaningless. The Collaboration score is built on an absolute scale, unlike Effort and Consistency, which are shrunk model outputs. | **Yes**: after seeing the calibration, before any agreement or firing result was computed. |
| 2026-10-19 | **Extension A, Last-minute rusher second path** (rules version 2). The rule fires when (E > E_med and C < C_low) **or** (E > E_med and late-churn share >= DC_high). Late-churn share is the Consistency package's `C_DC` (share of the sprint's churn in its last 3 days), used only when the student had activity (`C_no_activity` = 0; a student with no activity gets the worst value 1 by construction). E_med is the cohort median Effort and DC_high the 70th percentile of `C_DC` among active student-sprints, both from the 144 real student-sprints only. Strength is the smaller of the two margins of the path that matched. The proposal's own condition is kept as the first path, with E_high replaced by E_med only if the extension is kept. | First run: Last-minute rusher never fired (recall 0 of 52 labelled records): those records have median Effort 0.36 and median Consistency 0.21 while the rule needs Effort above 0.54 and Consistency below 0.05. Concentration of work at the end of the sprint is what defines a rusher and `C_DC` measures exactly that; it is already computed by the Consistency package. | **Yes**: designed after seeing the first agreement results. To limit fitting to the labels, the new cut points come from the real records only and the change is judged on the simulated records (175, labels from the behaviour classes they were written to follow), not on the records it was designed on. **Keep only if** on the simulated records Last-minute rusher recall is at least 0.30 and its precision at least 0.50 and no other pattern loses more than 0.05 recall; otherwise revert and report. |
| 2026-10-19 | **Extension B, Free rider when Collaboration is not available.** If Collaboration is not available and E < E_low and C < C_low, the pattern is Free rider with `evidence = "effort_only"` and a milder modifier range 0.95 -> 0.90 (weak -> strong). With a Collaboration score the original rule and range are unchanged. | A student with almost no observable activity (labelled Free riders sit at Effort 0.02, Consistency 0) was called Balanced contributor whenever the team did not review, which is 77% of them. The absence of team reviews says nothing about the student, but the absence of any commits or tasks does. The range is milder than the proposal's because the second half of the proposal's condition (low collaboration) could not be checked. | **Yes**: same point in time. **Keep only if** Free rider recall on all labelled records rises and precision stays at least 0.60; otherwise revert and report. |
| 2026-10-19 | **Outcome of the keep/revert checks (notebook 3, `results/extension_decision.json`).** Extension A (Last-minute rusher second path) **not adopted**: on the simulated records its recall is 0.30 (criterion: at least 0.30, met) but its precision is 0.47 (criterion: at least 0.50, missed by 0.03); no other pattern lost recall. Extension B (effort-only Free rider) **adopted**: Free rider recall on all labelled records rose from 0.20 to 0.88 with precision 0.88 (criterion: precision at least 0.60). The stored default set `calibrated` therefore has `ext_free_rider` on and `ext_rusher` off; `calibrated_AB` (both) and `calibrated_v1` (neither) are kept in `thresholds.json` for comparison. | The criteria were fixed before the code was written, so a near miss is a miss. | n/a (applies the rule written above) |

This folder contains the Behavioral Pattern factor: a **rule-based classifier** (not a trained model) that assigns a contributor pattern to one student in one sprint and returns the score modifier the fusion step multiplies onto the final score (proposal 3.1.7).

## How it works

[rules.py](rules.py) holds the five rules of the proposal (Consistent deep contributor, Last-minute rusher, Reviewer or coordinator, Burst worker, Free rider; anything else is Balanced contributor), the modifier range of each, and the way a modifier is chosen inside its range (stronger evidence, further toward the strong end). [thresholds.json](thresholds.json) holds the fixed cut points: the `calibrated` set (Effort and Consistency cut points read as cohort quantiles, Collaboration at the proposal's 0.7 / 0.3) and the proposal's own numbers are kept for comparison. [evaluate.py](evaluate.py) is the entry point the agent's bridge calls (`classify`).

Rules the code enforces (decisions and reasons in [training/PROTOCOL.md](training/PROTOCOL.md)):
- Fixed numbers, never percentiles of the students being scored.
- A missing score is never replaced by 0 or by a typical value. Effort or Consistency missing: "Unclassified", modifier 1.00. **Collaboration not available** (nobody in the team reviewed in the sprint): the Reviewer and the full Free-rider rules cannot fire; the other three still can.
- **Effort-only Free rider** (adopted extension B): with Collaboration not available, Effort below its low cut and Consistency below its low cut still give Free rider, with a milder modifier (0.95 to 0.90 instead of 0.85 to 0.80), because having no commits or tasks is evidence on its own while having no reviews in the team is not.
- If two patterns match (Last-minute rusher or Consistent deep contributor together with Burst worker), the one with the milder modifier wins.
- The modifier is always inside the pattern's range and inside 0.80-1.20.
- Extension A (a second path to Last-minute rusher through the late-churn share) is implemented behind a switch but **not adopted**: it missed its pre-set precision criterion by 0.03 (0.47 against 0.50).

The agent's node ([com_agent/nodes/behavioral_node.py](../../com_agent/nodes/behavioral_node.py)) only gathers the scores (a factor that fell back counts as missing) and calls this package through the bridge; it holds no rules of its own.

`cleaning.py` checks the inputs (ranges, cleaning versions). Tests: `python -m unittest discover -s 06_behavioral_pattern/tests` from `factor_models/`. How this fits the agent: [../ARCHITECTURE.md](../ARCHITECTURE.md).

## What is known about it (training/experiments/exp01_threshold_calibration)

- With the proposal's cut points almost no rule fires on our scores (Effort above 0.7 in 7.5% of student-sprints, Consistency above 0.7 in 1.3%). The calibrated set gives a pattern to 40% of the 319 student-sprints (57 Consistent deep contributors, 61 Free riders, 6 Reviewers, 4 Burst workers, no Last-minute rushers).
- Agreement with assistant-written labels (a pipeline check, not validation): accuracy 0.44 on the simulated behaviour classes and 0.45 on the 299 labelled records, kappa 0.30 and 0.35, against 0.31 / 0.14 and 0.20 / 0.06 for the proposal's cut points. When a rule fires it is usually right (precision 0.72 to 0.88).
- **Still weak:** Last-minute rusher never fires (its labelled records have a median Effort of only 0.36) and Burst worker finds 4 of 65 labelled records. These need instructor judgements to decide whether the labels or the rules are wrong.
- Collaboration is not available for 136 of the 144 real student-sprints, so the Reviewer rule and the full Free-rider rule can hardly be tested on real data.
- The modifier adjusts rather than reorders (Spearman 0.99 with and without it; largest change 9.2 points).
- **Not validated against instructors.** Every label is assistant-written. The study the proposal asks for needs [training/dataset/INSTRUCTOR_FORM.md](training/dataset/INSTRUCTOR_FORM.md).

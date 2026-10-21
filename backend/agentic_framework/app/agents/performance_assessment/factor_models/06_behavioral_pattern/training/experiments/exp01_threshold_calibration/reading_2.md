**Calibrated cut points** (written to `thresholds.json`): Effort high 0.543, mid 0.309, low 0.198; Consistency high 0.318, low 0.053; Collaboration 0.7 / 0.3.

**Two things the calibration showed.**
1. The quantile reading of Collaboration was degenerate: 77 of the 133 available scores equal 0.25 (the response-rate measure of the Collaboration score gives that value to anyone who only merged their own pull requests), so the 30th and 70th percentiles are both 0.25. A Reviewer rule (above 0.25) and a Free-rider rule (below 0.25) cut at the same point would be meaningless. Collaboration therefore keeps the proposal's absolute 0.7 / 0.3; this change was made before any agreement figure was computed and is in the amendment log of the protocol.
2. The Consistency low cut is 0.053 because a quarter of the real student-sprints have a Consistency of exactly 0 (no activity). A rule that needs Consistency below 0.053 together with Effort above 0.543 can hardly be met, which matters for the Last-minute rusher rule (see the next notebook).

These cut points describe the 144 real student-sprints of one course. They are fixed numbers now and will not move when other students are scored; they should be recomputed, with the same stated rule, when a new cohort is added.

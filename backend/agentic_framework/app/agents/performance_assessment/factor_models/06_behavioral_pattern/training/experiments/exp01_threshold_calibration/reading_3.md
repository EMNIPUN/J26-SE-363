**Firing (319 student-sprints).** With the proposal's cut points almost nothing fires: 2 Consistent deep contributor, 1 Last-minute rusher, 7 Reviewer or coordinator, 2 Burst worker, 26 Free rider, 281 Balanced. The final calibrated set (original rules plus the effort-only Free rider path) gives 57, 0, 6, 4, 61 and 191. The old rules in the dataset fired Free rider 96 times.

**Agreement with the assistant labels** (a pipeline check only; the labels come from the same kind of reasoning as the rules, so this is not instructor validation):

| Thresholds | simulated classes (accuracy, kappa) | reference pattern, all | reference pattern, Collaboration available | 20 anchors |
|---|---|---|---|---|
| proposal | 0.31, 0.14 | 0.20, 0.06 | 0.25, 0.13 | 0.20, 0.00 |
| calibrated v1 (original rules) | 0.42, 0.27 | 0.33, 0.21 | 0.41, 0.31 | 0.40, 0.25 |
| **calibrated (adopted: + effort-only Free rider)** | 0.44, 0.30 | 0.45, 0.35 | 0.41, 0.31 | 0.65, 0.56 |
| calibrated AB (both extensions, not adopted) | 0.49, 0.37 | 0.49, 0.39 | 0.46, 0.36 | 0.80, 0.74 |

**Per pattern (adopted set, all labelled records).** Consistent deep contributor: recall 0.68, precision 0.72. Reviewer or coordinator: recall 0.19, precision 0.83. Burst worker: recall 0.05, precision 0.75. Free rider: recall 0.88, precision 0.88. Last-minute rusher: never fires (recall 0). When a rule fires it is usually right; two of the five patterns still fire rarely or never.

**The two extensions, judged by the criteria written before they were implemented.** Extension B (Free rider on effort alone when Collaboration is not available) raised Free rider recall from 0.20 to 0.88 at precision 0.88: adopted. Extension A (a second path to Last-minute rusher through the late-churn share `C_DC`) reached recall 0.30 and precision 0.47 on the simulated records, where the criteria asked for at least 0.30 and 0.50: not adopted, by 0.03. Had both been kept, accuracy would be higher (0.49 on the simulated classes, 0.80 on the anchors), but that figure also includes the records Extension A was designed on, so it is the optimistic one.

**Why the remaining misses.** The records labelled Last-minute rusher have a median Effort of 0.36 and a median Consistency of 0.21 (the rule needs Effort above 0.54 and Consistency below 0.05). The Effort and Consistency marks do not separate a rusher from a balanced contributor by thresholds alone. Labelled Burst workers have the bimodal flag in only 32% of cases, and 65 records carry that label against 4 that the rule finds.

**What this means.** The rules are implemented as specified and behave consistently; read on this data, the proposal's rules find Consistent deep contributors, strong reviewers and (with the effort-only path) non-contributors, and miss rushers and burst workers because of how the underlying scores are distributed. Whether instructors would call these records rushers or burst workers is what the instructor study of the proposal has to answer.

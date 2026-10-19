# Behavioral Pattern: instructor judgement form (the proposal's validation, not yet done)

The proposal validates Behavioral Pattern by comparing the rule's pattern with independent instructor judgements; disagreements are reported as findings, not hidden. This form is
for that study. Nothing in this repository has been rated by an instructor yet: every label in `bp_inputs.csv` was written by the assistant.

## Who and how many

- At least two instructors per student-sprint, rating independently (so that agreement between instructors can be reported with Cohen's kappa, the proposal's inter-rater check).
- At least 40 student-sprints, chosen so that every pattern the rules can output appears; include sprints from teams with and without code review.
- The instructor does **not** see the rule's pattern, the factor scores or the modifier. Show the sprint's evidence: the activity strip (commits per day), the tasks and their status,
  and the pull requests and reviews of the team.

## Per student-sprint

Choose the one pattern that best describes this student's behaviour in this sprint (or "none of these"):

| Pattern | Describe it as |
|---|---|
| Consistent deep contributor | Substantial work, spread steadily over the sprint |
| Last-minute rusher | Substantial work, but almost all of it in the last days |
| Reviewer or coordinator | Little code of their own, but reviews, comments and coordinates with teammates |
| Burst worker | Substantial work, in separate bursts with quiet periods between |
| Free rider | Almost no observable contribution of any kind |
| None of these | Ordinary, middle-range contribution |

Also: how confident are you (1 = guess, 3 = sure)? Any note.

## Analysis (prepared in `training/experiments/exp01_threshold_calibration/03_firing_and_agreement.ipynb`)

Pattern from the rule against the instructors' pattern: accuracy, Cohen's kappa, per-pattern recall and precision and the confusion matrix, for the proposal's thresholds and the
calibrated ones, and the instructors' agreement with each other. Every disagreement is listed with its scores; the cut points are revisited only with these judgements as evidence.

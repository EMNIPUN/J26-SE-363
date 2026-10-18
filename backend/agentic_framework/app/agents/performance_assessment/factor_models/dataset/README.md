# Assessment dataset: all seven factors

The data behind the individual performance assessment: real student sprints from 14 team
projects, a reconstructed Scrum board, the features of every factor, a balanced synthetic set,
20 rated reference records, and marks for every record.

Everything here is pseudonymous. Students are `STU-xxx`, teams `Txx`, repositories `Rxx`.
Real identities and raw repository data are only in `private/`, which is git-ignored and must
never be committed, shared or published.

## Files

| File | What it is |
| --- | --- |
| `sprints.csv` | 36 two-week sprints across 14 teams (project domain only, no project names) |
| `roster.csv` | Which student was in which team |
| `evidence/` | Pseudonymised commits, files changed, pull requests, reviews and comments |
| `scrum_board.csv` | The reconstructed Scrum board: 347 tasks (also per team in `scrum_board/`) |
| `features_real.csv` | One row per student per sprint (144 rows) with every factor's features |
| `features_real_profiles.csv` | The provisional profile of each real record, used for balancing and sampling |
| `synthetic_dataset.csv` | 600 synthetic records, 100 per profile |
| `ground_truth/samples.csv` | The 20 records chosen for rating |
| `ground_truth/EVALUATION_FORM.md` | The form a rater fills in for those 20 |
| `ground_truth/human_ratings.csv` | Ratings of the 20 (see "Ground truth" below) |
| `ground_truth/human_ratings_template.csv` | Empty sheet for a real rater |
| `marks_report.json` | Fitted models, cross-validated accuracy, weights, pattern agreement |
| `final_dataset.csv` | Every record (real and synthetic): all features, all factor scores with intervals, pattern, final mark |
| `private/` | Identity map, real repository locations, raw cache. **Git-ignored** |

## Pipeline

Run from `scripts/` with Python 3.11+ and `numpy`, `scipy` (steps 6 only).

```
python 01_extract_evidence.py      # git history (all branches) + GitHub PRs, reviews, comments -> private/raw
python 02_build_evidence.py        # pseudonymised evidence/*.csv
# (the Scrum board in scrum_board/ is written by hand from the evidence; see below)
python 03_compute_features.py      # features_real.csv, scrum_board.csv, roster.csv
python 04_synthesize.py --per-profile 100 --seed 7
python 05_build_ground_truth.py    # samples, form, empty rating sheet
python 06_propagate_marks.py       # marks_report.json, final_dataset.csv
```

`digest.py T03` prints one team's evidence student by student; it is what the board was written
from.

## Data

- **Source.** 20 local repositories (all branches) and their GitHub pull requests. 14 team
  projects, 28 students, 1,957 commits, 315 pull requests.
- **Excluded.** One project with 2 commits, and two single-author projects (not team work).
- **Identity.** Authors with several emails or accounts were merged by email, GitHub login and
  name. One account that is not on any roster continues a rostered student's work, so it was
  merged into that student; the decision is recorded in the private map.
- **Sprints.** 14-day windows placed over each team's activity. Commits outside every window
  (35) are kept in the evidence but not scored. Every rostered member gets a record for every
  sprint, so inactive members appear as records with no activity (37 of 144).
- **What counts as code.** Generated, vendored and binary files are excluded from line and
  file counts: `node_modules`, build output, lockfiles, committed database folders, the Maven
  wrapper, images and similar. A commit touching more than 150 counted files is marked `bulk`
  (a re-upload or a scaffold). Bulk commits are counted but contribute no lines.

## The Scrum board (reconstructed)

The teams did not keep a usable board, so it was rebuilt, team by team and student by student,
from the commits, branch names and pull requests. Each task has a `basis`:

| basis | Tasks | Meaning |
| --- | --- | --- |
| `github_issue` | 19 | Taken from the team's real GitHub issues (one team kept a sprint backlog) |
| `commit_evidence` | 291 | Inferred from what the student's commits built |
| `assumed_allocation` | 37 | A plausible task in the student's area of the system, for members with no work that sprint |

Rules followed:

- **Status.** Status is what the code shows at sprint end: 258 Done, 40 Partially Done,
  3 In Progress, 46 To Do. Commits after the sprint do not make a task Done.
- **Carry-over.** Unfinished work carries into the next sprint (29 tasks).
- **Completed by someone else.** When a teammate did the work, `completed_by` names them
  (6 tasks), and the assignee gets no credit for it.
- **Fulfilment rating.** `ac_total`, `ac_met` and `llm_fulfilment_rating` (1–5) are the
  reconstructor's judgement of the diff against the criteria. This stands in for the LLM
  judge in proposal 3.1.4.
- **No perfect students.** No student completes everything flawlessly; the notes record what
  was missing.

**Limitation.** The board is a reconstruction. Story points, criteria and the 37 assumed tasks
were not set by the teams at the time.

## Features

Every column carries its factor prefix. Definitions follow the proposal (section 3.1); deviations
are marked.

| Factor | Features | Notes |
| --- | --- | --- |
| Effort | `E_CC` commits, `E_LOC_net` and `E_LOC_net_capped` (each commit capped at ±800), `E_FC` files, `E_CT` own tasks done, `E_RD` reviews + comments + teammates' PRs merged | Bulk commits excluded from lines and files |
| Consistency | `C_AWR` active days / 14, `C_DC` share of churn in the last 3 days, `C_LI_norm` longest idle run / 14, `C_CV_norm` daily-churn CV / √13, `C_bimodal` | No activity → worst values and `C_no_activity = 1` |
| Requirement fulfilment | `RF_llm_score` (mean (rating−1)/4), `RF_completion_rate`, `RF_ac_ratio`, `RF_untracked_ratio`, task counts | |
| Collaboration | `Co_PRC_depth`, `Co_IC_depth` (0–1 substance), `Co_MC`, `Co_PCount`, `Co_CCount`, `Co_IR`; plus `Co_shared_file_ratio`, `Co_prs_merged_for_others` | **Deviation:** comment substance is rule-based, standing in for the encoder. Added two git-based features because review text barely exists |
| Task complexity | `TC_SP`, `TC_SC`, `TC_FI` files, `TC_DR` dependency reach, `TC_CB` components | `TC_DR`: files importing the changed files (up to two hops) in the import graph at sprint start |
| Code ownership | `KO_survival`, `KO_primary_owner_share`, `KO_snippet_candidates` | **Deviation:** passive only (blame at the final version). `KO_quiz_score` is empty: past students cannot be interviewed |
| Behavioral pattern | none of its own | Derived from the scores in step 6 |

**Findings worth reporting.**

- **Almost no written review.** The whole cohort produced 12 reviews and 1 human comment, all
  approvals such as "ok". So `Co_PRC_depth`, `Co_IC_depth` and `Co_MC` are zero for everyone.
  `Co_IR` is almost always 1, because pull requests are self-merged.
- **Little task-free work.** `RF_untracked_ratio` is near zero because the board was built from
  the commits.

## Synthetic set

- **Profiles.** Each real record gets a provisional profile from cohort-percentile indices of
  effort, consistency and collaboration (`profiles.py`, a feature-level reading of proposal
  3.1.7). Real counts: consistent deep 19, last-minute 13, burst 4, reviewer/coordinator 3,
  free rider 39, no specific pattern 66.
- **Generation (SMOTE).** Each synthetic record interpolates two real records of the same
  profile at a random point, with 5% noise. It is then repaired so it is a possible sprint:
  whole counts, ratios in 0–1, no commits means no code, tasks done ≤ tasks assigned, and so on.
  Candidates that leave their profile (21) or look perfect on every factor (0) are rejected.
- **Limitation.** Burst workers and reviewer/coordinators come from only 4 and 3 real seeds, so
  those 200 records add little new information. `seed_records` says how many seeds each record
  came from.
- **No labels.** Synthetic records carry no ratings. Their marks come from step 6, exactly like
  the real records'.

## Ground truth (20 records)

- **Selection** (`05_build_ground_truth.py`): real records only; stratified by profile; at most
  two per team and one per student; spread across the effort range within each profile. Members
  of the research team are excluded. Candidates appear in random order.
- **Form.** The form gives what a supervisor would see on GitHub and the board: tasks and
  status, a 14-day activity strip, how much code, sample commit messages, pull requests and
  reviews, and whether the code lasted. It does not show the model's computed features. Each
  factor has 3–5 criteria rated 1–5 (5 is described as rare), plus a pattern and an overall
  mark.

To use ratings from other raters, enter them in `human_ratings_template.csv`, save it as
`human_ratings.csv` and rerun step 6. With two raters, report the agreement between them (ICC) and
average their ratings.

## Marks for every record (step 6)

The method, which you can describe to the panel as *anchor-based label propagation*:

1. **Factor targets.** For each factor, the rater's criteria are averaged and rescaled to 0–1:
   `Factor_GT = (R_avg − 1) / 4`, as in the proposal.
2. **Ridge per factor.** A ridge regression maps the factor's own features to that target.
   Features are log-transformed where skewed, standardised against the real cohort, and missing
   values take the cohort median. The penalty is chosen by leave-one-out cross-validation
   (LOOCV) over the 20 anchors.
3. **Marking every record.** The fitted model marks every real and synthetic record, clipped to
   0–1. A bootstrap over the anchors (1,000 resamples) gives each score a 90% interval
   (`*_score_lo`, `*_score_hi`).
4. **Extrapolation flag.** `*_extrapolated = 1` when a feature the model uses is more than 25%
   outside the anchors' range. Treat those marks with more caution.
5. **Behavioral Pattern.** The proposal's rules are applied to the scores.
   - The fixed 0.7 thresholds almost never fire on this scale: calibrated scores average about
     0.4.
   - So "high" is the cohort's 70th percentile (at least 0.35), and "low" stays at the
     proposal's 0.3.
   - Both versions are reported. These thresholds were chosen after looking at disagreements
     with the 20 ratings, so the agreement below is optimistic.
6. **Fusion.** Weights are fitted by non-negative least squares on the rater's overall marks
   (after removing the pattern modifier), then normalised to sum to 1. The final mark is
   `100 × BP_modifier × Σ wₖ · factorₖ`.

**Results with the current ratings.** All figures are leave-one-out, so each is
measured on a record the model did not see.

| Factor | LOOCV MAE (0–1) | LOOCV Pearson | MAE of always predicting the mean |
| --- | --- | --- | --- |
| Effort | 0.048 | 0.97 | 0.219 |
| Consistency | 0.062 | 0.92 | 0.192 |
| Requirement fulfilment | 0.053 | 0.97 | 0.239 |
| Collaboration | 0.090 | 0.62 | 0.128 |
| Task complexity | 0.092 | 0.47 | 0.119 |
| Code ownership | 0.105 | 0.89 | 0.242 |

- **Final mark, end to end.** Factor scores, weights and pattern all come from the other 19
  records each time. MAE 6.7 / 100, RMSE 8.3, Pearson 0.97, Spearman 0.91. The system marks
  5.4 points lower than the rater on average.
- **Weights learned.**

  | Factor | Weight |
  | --- | --- |
  | Requirement fulfilment | 0.40 |
  | Effort | 0.18 |
  | Task complexity | 0.16 |
  | Code ownership | 0.16 |
  | Collaboration | 0.07 |
  | Consistency | 0.03 |

  Equal weights would double the error (11.2 against 5.9).
- **Behavioral Pattern.**
  - Proposal thresholds: 40% agreement with the rater, Cohen's kappa 0.23.
  - Cohort thresholds: 50% agreement, kappa 0.36.
  - The rules rarely reproduce the rater's "last-minute rusher".
- **No perfect students.** Final marks range 6–83 for real records and 5–84 for synthetic ones.

## What these numbers do and do not show

- **One rater.** There is no inter-rater reliability yet. The proposal's ICC needs at least two
  raters.
- **Optimistic agreement.** Effort, Consistency, Requirement fulfilment and Code ownership agree
  well partly because the rater read evidence built from the same commits as the features
  (activity strip, code size, task status). The form hides the computed values, but the
  underlying evidence is shared. With a human rater, expect lower figures.
- **Weak factors.** Collaboration and Task Complexity are only moderately learnable: the cohort
  barely reviews, and task difficulty is hard to see from commits. Report this as a finding,
  not a flaw to hide.
- **20 anchors.** Twenty anchors support ridge models with three to eight features, but the
  intervals are wide. Read the `*_lo` and `*_hi` columns.
- **Code Ownership is half-built.** It is only the passive half here. The comprehension quiz
  (the novel part of the proposal) needs live students and will add `KO_quiz_score`.

**What you can defend to the panel.** Twenty records were rated in full on a rubric, chosen to
cover every behaviour type and team. Each factor's mark was propagated to every other student by
a model whose error was measured by leave-one-out cross-validation on records it never saw.
Every propagated mark carries a bootstrap interval and an extrapolation flag. This is a
standard, disclosed way to extend a small expert-labelled sample. It is stronger with two human
raters and their agreement reported.

## Clean features (steps 9-12) and simulated students

The tables above count lines the way git does (comments, blank lines, markdown and configuration included). The clean tables
count only real work, through each factor package's own cleaning code (see `../ARCHITECTURE.md`):

| Step | Script | Output |
|---|---|---|
| 9 | `scripts/09_clean_commit_stats.py` | `clean/commit_file_stats.csv`: per commit and file, added and deleted lines split into code, comment, blank, format-only (counts only) |
| 11 | `scripts/11_clean_blame_real.py` | clean blame at the final version (in `private/cache`, git-ignored) |
| 10 | `scripts/10_features_clean_real.py` | `clean/features_real_clean.csv`: 144 real student-sprints, with the old values beside the new in `*_raw` columns |
| - | `synthetic_students/materialize.py` | `synthetic_students/out/features_simulated_clean.csv`: 175 simulated student-sprints |
| 12 | `scripts/12_refit_labels_clean.py` | `clean/final_dataset_clean.csv` (real and simulated, features, estimated marks, intervals) and `clean/marks_report_clean.json` |

On the real students cleaning lowers the counted work: lines by about 20%, commits by 23% and files by 24% (docs-only and
reformat-only commits stop counting). The 600 blended synthetic rows of `synthetic_dataset.csv` are not part of the clean set;
the 50 simulated students replace them. Run with `../01_effort/.venv/Scripts/python.exe`.

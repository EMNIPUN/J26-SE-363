# Simulated students (50)

Fifty students added beside the 26 real ones, which are untouched. Each was written one by one: a team
project with a Scrum board (tasks with descriptions, acceptance criteria, story points, subtasks), commits
with the files and lines they touch, code for the core of each task, pull-request reviews and comments, and a
code-ownership quiz question with the student's answer. Nothing here is real student data and no names appear;
ids are `SYN-001` to `SYN-050`.

| Folder / file | What it is |
|---|---|
| `teams/S01.py` ... `S10.py` | The hand-written source: ten teams of five, 2 to 5 sprints each (see `out/validation_report.md`) |
| `teams/_kit.py` | Small constructors that only build dicts and tuples |
| `materialize.py` | Computes every feature from the written commits, tasks, reviews and quiz answers with the same formulas as the real pipeline, and checks the source for mistakes |
| `compare_with_real.py` | Compares feature ranges and rule-based profiles with the real students |
| `out/features_simulated.csv` | One row per student per sprint, same columns as `features_real.csv`, plus `KO_quiz_score` |
| `out/scrum_board_simulated.csv`, `out/code_examples.jsonl` | The tasks, and the code written for each with which criteria it meets |
| `out/commits_simulated.csv`, `reviews_simulated.csv`, `comments_simulated.csv`, `pull_requests_simulated.csv`, `quiz_simulated.csv`, `students_simulated.csv` | The evidence behind the features |

## What the simulated students are for

- To give the factors with no real data (Requirement Fulfilment, Collaboration text, Code Ownership quiz,
  Behavioural Pattern rules) code, tasks, reviews and answers whose quality is known by construction.
- To cover behaviour the 26 real students do not: all six classes and the in-between cases (steady but small,
  big but late, strong start then stops, hard task with little code, easy task with a lot of code, solid coder who
  never reviews, a team that does not use pull requests, a pasted library, a task finished by a teammate, a late
  joiner, a granular committer).
- Every student has at least one flaw. `out/validation_report.md` lists records where every factor looks strong:
  there are none.

## What they are not

- They carry **no ratings**. Any marks for them would be estimates, so accuracy must still be measured on the
  20 real rated records only.
- They are not interchangeable with the real records on every feature. The share of tasks left partial is 32% against
  12% in the real board and tasks never started are 5% against 13%, so criteria met is lower (0.75 vs 0.93). Records with
  survival under 0.5 are 15% against 27%. See `compare_with_real.py`.

## Re-running

```
../../01_effort/.venv/Scripts/python.exe materialize.py
../../01_effort/.venv/Scripts/python.exe compare_with_real.py
```

## Volume

The hand-written commits list the core of each change, so on their own they were about ten times smaller than real
commits. `volume.py` sets, for each student separately (never per team, teammates are not used), the typical net
lines per active sprint that student reaches, chosen from the real students of the same type. `materialize.py`
scales the student's own commits to that level, adds the neighbouring files each change touches (from the team's
import graph, plus its tests, stylesheet and fixture), and lets heavy committers split one piece of work into
several same-day commits. `out/volume_applied.csv` shows the scale used for each student, and
`out/commits_simulated.csv` shows the resulting commits. Remaining gaps against the real students: files per
sprint (15 vs 32), commits per sprint for light committers (4 vs 7), and component breadth (4 vs 5).

## Task Complexity

Built to the proposal's definition: the structure of a task is measured on the repository as it stood **before the
task started**, and the label is the mean of five ratings (technical difficulty, scope and breadth, dependency impact,
architectural impact, uncertainty), `TC_GT = (R_avg - 1) / 4`.

| File | What it holds |
|---|---|
| `complexity_ratings.py` | The five ratings for each of the 219 tasks, given from what the task asks for (not who did it, how well, or its story points). A task carried into a later sprint keeps its ratings. |
| `board_estimates.py` | The teams' own story points and subtask counts where they differ from difficulty (padded easy work, under-estimated hard work); other subtask counts are squeezed into the real 1-4 range |
| `out/task_complexity_tasks.csv` | One row per task: story points, subtasks, files involved, dependency reach, component breadth, the five ratings, `R_avg`, `TC_GT` |
| `out/features_simulated.csv` | `TC_*` columns per student-sprint (mean over the student's tasks) and `TC_authored_score` |

Files involved, dependency reach and component breadth use the commits as written, never the volume-scaled ones, so
they cannot grow with how much a student writes. Dependency reach counts only files that already existed when the
task's first commit was made, as in the real data (where most tasks touch new files, so the median is 2).
Tasks with no commits have no footprint (12 of 175 records), as in the real data.

The ratings are authored estimates, not assessor ratings; accuracy must still be measured on the 20 real rated records.

## Code Ownership and Requirement Fulfilment values

- `ownership.py` gives survival and primary-owner share for every student and sprint, with the reason for the low
  ones (rewritten, reverted, pasted or replaced code). Earlier sprints have had longer to be rewritten, last-minute
  work is written late and survives better, and reviewers' small changes are most often refactored by others.
  Medians by type now match the real students (survival: consistent 0.70 vs 0.72, rusher 0.85 vs 0.85, burst 0.68 vs
  0.67, no pattern 0.72 vs 0.70, reviewer 0.45 vs 0.39).
- `fulfilment.py` rates fulfilment on the real board's 1-4 scale, following the criteria met: nothing built is 1,
  partial work 2, all criteria met 3, all met by clearly strong work 4. Done tasks average 3.25 (real 3.05).

## Clean features for the simulated students

`to_evidence.py` writes each simulated student-sprint as raw evidence (`evidence/1`) and `materialize.py` passes it through the same
`featurize` code as the real students, giving `out/features_simulated_clean.csv`. The hand-written commits state only how many lines
each file changed, so the split of those lines into code, comment, blank and format-only comes from the real repositories by file
type (file types with too little real data use the shares of all source files; see `out/split_fallbacks.txt`). The footprint of a
task assumes four companion modules (helpers, types, constants, utils) beside each source file, because real tasks touch about 13
source files and the small simulated projects have fewer. Survival and ownership are the values in `ownership.py`; ratings are on the
real 1-4 scale (`fulfilment.py`). These are stated assumptions, the same for every simulated student.

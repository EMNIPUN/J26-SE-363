# Factor models: how the agent, the cleaning and the models fit together

Read this first if you have forgotten how the pieces connect. It covers the decision about where cleaning happens, the
evidence the agent hands to a factor tool, what each factor cleans, how the training data is built with the same code, and
what is still to be built.

## 1. The decision in one paragraph

Student repositories contain a lot that is not work: comment lines, blank lines, markdown, configuration, generated files,
reformatted or moved code, trivial commits. Models trained on counts that include this would be gamed by padding, and models
trained on dirty counts but fed clean ones at run time would under-score everyone. So **the agent never computes features and
never cleans.** It fetches raw evidence and calls a factor tool with a reference to it. **Each factor package owns its cleaning,
its feature definitions and its model**, and the training pipeline calls the very same cleaning code. Cleaning is never a tool
the agent chooses to call, and never something a language model does: student text and comments are untrusted, so a language
model must not read them in order to clean them.

## 2. The flow

```
 Agent (LangGraph, com_agent)                         Factor package (this folder, one per factor)
 ───────────────────────────────                      ────────────────────────────────────────────
 ingestion: clone repo, GitHub, Scrum
   store RAW evidence in the evidence pool  ───────►  assess_<factor>(evidence_ref)
   (patches or line counts, nothing cleaned)            1. schema.validate(evidence)
                                                        2. cleaning.featurize(evidence)   ← clean + features
 agent never sees raw diffs or student text             3. model.predict(features)        ← trained on the same featurize()
   in its language-model context                        4. result {score, interval, features,
 fusion, behavioural pattern, explanation  ◄──────────        removed, versions, warnings}
```

What each side owns:

| | Agent | Factor package |
|---|---|---|
| Which student and sprint to assess | yes | |
| Cloning, GitHub and Scrum fetching; storing raw evidence | yes | |
| Cleaning rules and feature definitions | | yes (`cleaning.py`) |
| Model, interval, versions | | yes |
| Missing-evidence fallbacks (`policies/fallback_policies.py`) | yes | |
| Fusion, behavioural modifier, explanation (uses `removed`) | yes | |

## 3. Layout

```
factor_models/
  evidence/                 shared contract and line-level primitives (no model, no network)
    lines.py                classify_path, stats_from_patch, clean_patch, strip_comments_and_blanks, CLEANING_VERSION
    schema.py               the evidence contract (evidence/1) and validate()
    common.py               meaningful commits, per-file clean counts, day index
    registry.py             load_factors(): imports each factor's cleaning.py (folder names start with digits)
    testing.py, tests/      builders and tests
  01_effort/cleaning.py     what counts as effort            + tests/
  02_consistency/cleaning.py   active days and rhythm        + tests/
  03_requirement_fulfillment/cleaning.py   the diff a judge reads, board features   + tests/
  04_collaboration/cleaning.py   review and comment text cleaning, features          + tests/
  04_collaboration/score.py, evaluate.py   fixed-weight score with an evidence gate; the agent entry point
  05_task_complexity/cleaning.py   task footprint before the task started           + tests/
  06_behavioral_pattern/cleaning.py   input checks only (reads the other factors)    + tests/
  06_behavioral_pattern/rules.py, thresholds.json, evaluate.py   the five rules, fixed cut points, the agent entry point (`classify`)
  07_code_ownership/cleaning.py   blame on counted lines, quiz snippet selection     + tests/
  07_code_ownership/quiz.py, questions.py, score.py, evaluate.py, model/   AST question, guards + CodeBERT/SVR answer rating, agent entry point, trained head
  dataset/                  how the training data was built (see its README)
  ml_lib/                   model-agnostic training utilities (splits, metrics)
```

Every `cleaning.py` exposes `featurize(evidence) -> {features, removed, versions, warnings}` (BP exposes `validate_inputs`).

## 4. The evidence contract (`evidence/1`)

Full description in `evidence/schema.py`. In short, for one student in one sprint:

- `commits[]`: id, authored_at (with offset), is_merge, subject, and `files[]` with path, added, deleted and **either a unified
  diff (`patch`) or precomputed `line_stats`** (added and deleted lines split into code / comment / blank / format_only).
- `tasks[]`: board fields (story points, subtasks, status, assignee, completed_by, carried_over_from, acceptance criteria,
  commit_ids), optionally a judge rating and `criteria_met`, optionally a `footprint` (cleaned files with `reach_before`).
- `task_commits[]`: commits by teammates that implement the student's tasks (a task's structure belongs to the task).
- `pull_requests[]`, `reviews[]`, `comments[]`, `merged_for_others`.
- `ownership`: `{added_lines, surviving_lines, files, primary_files, owned_files}` from blame on counted lines.
- `repo.reach_before`: dependency reach per file on the repository before the sprint (source files only).

The two forms of a file's lines exist because of how the data was made: at run time ingestion has the real diff and
`evidence.lines.stats_from_patch` gives the counts; the simulated students have no diffs, only counts.

Result of a factor tool: `{factor, score, interval, features, removed, versions: {cleaning, features, model}, warnings}`.

## 5. What each factor cleans

| Factor | Counts | Does not count | Notes |
|---|---|---|---|
| **Effort** | `code` lines in source (`code`, `test`) files; commits with at least one counted line; files with a counted change; per-commit net capped at 800 | comment-only and docstring lines, commented-out code, blank lines, moved or re-indented lines, docs, config, generated, assets, data, merge commits, bulk uploads (>150 source files) | a README-only or reformat-only commit is not effort |
| **Consistency** | days with a counted commit; daily size = counted lines changed (≤800 per commit) | days with only docs or reformatting; commits outside the sprint window | day taken from the commit's own local date |
| **Requirement Fulfilment** | board fields; judge sees only the cleaned source diff | comments, docs, config, generated, moved lines in the diff; work done by a teammate is not credited | diff cut at 12,000 characters with a marker; judge rating is 1-4 |
| **Collaboration** | the student's reviews and comments on other people's pull requests | bots, self-comments, quoted replies, code blocks, links, mentions, emoji, repeated-word padding, approvals ("LGTM") | encoder takes the same cleaned text. Shared-file ratio is not used (depends on teammates) |
| **Task Complexity** | `code` files a task changes with a counted line; reach on the pre-task import graph (source files only, two hops); components; team's story points and subtasks | tests, docs, config, generated, comment-only files; files that did not exist yet have no reach | a task with no commits has missing structure, not zero |
| **Code Ownership** | blame (`-w`, format-only commits ignored) on counted lines at the final version | blank, comment, docstring lines; non-source files | quiz snippets: real logic, ≥8 counted lines, no getters/setters/shells |
| **Behavioural Pattern** | the other factors' scores and the `C_bimodal` flag | | validates inputs and cleaning versions. Thresholds must become fixed numbers before single-student use (see §8) |

## 6. Versioning and the training match

- `evidence/lines.py: CLEANING_VERSION` identifies the cleaning rules; each factor has its own `FEATURES_VERSION`.
- **Bump `CLEANING_VERSION` whenever any rule changes** (what counts as a comment, the format-only rule, file kinds...). Then
  rebuild the training features (§7), refit labels, retrain, and store the new version with the model.
- A saved model must record the cleaning and features versions it was trained with. `factor_bridge.py` (to be extended, §9) must
  refuse to score features prepared under a different version.
- `BehaviouralPattern.validate_inputs` already refuses mixed versions.

## 7. Building the training data (same code as run time)

Run from `dataset/` with `../01_effort/.venv/Scripts/python.exe` (the project environment):

| Step | Script | Output |
|---|---|---|
| 1-8 | `scripts/01..08_*.py` | the original evidence tables, features, ground truth, dirty-feature marks (kept for comparison) |
| 9 | `scripts/09_clean_commit_stats.py` | `clean/commit_file_stats.csv`: clean line counts per commit and file, from the diffs (counts only, no code) |
| 11 | `scripts/11_clean_blame_real.py` | `private/cache/blame_clean_*.json`: counted lines per author per file at the final version (private) |
| 10 | `scripts/10_features_clean_real.py` | `clean/features_real_clean.csv`: real students, through each factor's `featurize` |
| sim | `synthetic_students/materialize.py` | `synthetic_students/out/features_simulated_clean.csv`: simulated students, through the same `featurize` |
| 12 | `scripts/12_refit_labels_clean.py` | `clean/final_dataset_clean.csv`, `clean/marks_report_clean.json` |

Order: 9, 11, 10, then the simulated students, copy `features_simulated_clean.csv` to `clean/`, then 12.

The 20 rated records and their ratings do not change; only the features that predict them do, so the label model (ridge, penalty
by leave-one-out) is refitted. The old `final_dataset.csv` and `marks_report.json` are untouched.

## 8. Known limits and open items

- **Comment detection is line by line** with a small state for block comments and docstrings; no language parser is installed.
  A diff shows only changed lines, so a block comment that began before the change is recognised only when its lines start with `*`.
  A parser (for example tree-sitter) would be more exact for Effort and Ownership; installing one needs your approval.
- Cross-file moves and copy-paste from elsewhere are not detected. Format-only detection ignores lines shorter than six characters.
- Simulated students: the split of lines into code, comment, blank and format-only comes from the real repositories by file type
  (`synthetic_students/to_evidence.py`; file types with too little real data use the all-source shares, listed in
  `synthetic_students/out/split_fallbacks.txt`). Their task footprints assume four companion modules (helpers, types, constants,
  utils) beside each source file, because real tasks touch about 13 source files and the small simulated projects have fewer.
  Their ratings and marks are authored or estimated, never assessor ratings.
- Behavioural Pattern uses cohort percentile thresholds in the dataset scripts; they must become fixed numbers learned from the
  training cohort before the tool scores one student.
- Label model fits on the clean features are mixed (see the report): Effort slightly better; Collaboration, Task Complexity and
  Code Ownership slightly worse on the 20 anchors. The anchors were rated while looking at the old counts.

## 9. What is still to build for the agent

1. `evaluate.py` in each factor folder (**done for Collaboration**: `04_collaboration/evaluate.py` takes `evidence/1`, optionally with `evidence["team"] = {"reviews_and_comments": n}`
   (a count only, nothing about other students); when the team never reviewed it raises `NotEnoughEvidence`, the bridge applies its fallback and fusion redistributes the weight; feature payloads still go to `simulate.py`) (the bridge looks for `evaluate.py`, `predict.py` or `model.py`): load the trained model,
   call `schema.validate`, `cleaning.featurize`, `model.predict`, return the result in §4.
2. Extend `com_agent/ingestion/evidence_preparer.py`: store raw evidence in the contract's form (patches or `line_stats`,
   tasks with commit ids, blame-based `ownership`, `repo.reach_before` from an import graph of source files only) instead of
   only `net_human_loc`; replace `detect_dependencies_and_clean_loc` by `evidence.lines`.
3. `factor_bridge.py`: pass the evidence reference through, check `versions` against the model's stored versions.
4. Read-only explanation inputs: the `removed` summary (numbers only, never raw repository text).
5. Code Ownership is built end to end (question generation, answer rating, entry point, trained head); it needs torch, transformers, scikit-learn, joblib and the CodeBERT weights in the agent environment, and the agent supplies the student's source files (`ownership_files`) to the quiz node.
6. Retrain the models on `clean/final_dataset_clean.csv` with the existing protocols (tests scored once, on the real rated records).

## 10. Tests

From `factor_models/`: `python -m unittest discover -s evidence/tests` and the same for each `<factor>/tests`. They include
deliberate padding cases (comment spam, markdown padding, reformat-all, moved lines, quoted and linked comments).

# Requirement Fulfillment: experiments

Written 2026-10-19, before any language model was run on the benchmark. Changes after a model has been run go in the amendment log at
the end. Code: `rf_bench/` (shared benchmark, student-only tools, scorer, runner), one experiment per branch.

## Question

The proposal judges a task with one language-model call over the task text and the whole code diff. Real tasks are large: the cleaned
diff of a task has a median of about 800 changed lines (roughly 10,000 tokens), a 90th percentile of about 3,300 and a maximum above
20,000. The question is whether that design holds at real task sizes, and whether an agent that reads only what each criterion needs
does better. A third experiment adds a second model that checks the agent's verdicts.

| Branch | Experiment |
|---|---|
| `feature/requirement-fulfillment-sadeesha` | the shared benchmark and scorer; at the end, the best experiment |
| `feature/requirement-fulfillment-single-prompt-sadeesha` | Experiment 1: the proposal's single prompt |
| `feature/requirement-fulfillment-agent-experiment-sadeesha` | Experiment 2: a LangGraph agent with student-only tools |
| `feature/requirement-fulfillment-agent-critic-sadeesha` | Experiment 3: the agent plus an LLM-as-judge critic |

## What is shared (identical across experiments)

- **Benchmark** (`rf_bench/bench.py`, `benchmark/manifest.json`): 219 tasks of 50 simulated students in 10 teams, rebuilt
  deterministically and checked against the manifest's hash. Mock repositories: every commit of a team's sprint with message, files and cleaned
  changed lines; the deciding lines of each task sit among generic filler code; a task's cleaned diff follows the real size distribution
  (median 832, p90 3,124, maximum 17,412 lines in the build). Teammates' commits sit in the same sprint. 45% of commit messages name their
  task, the rest do not. No real student code is used anywhere; the filler is generated.
- **Truth**: the simulation's per-criterion `criteria_met`, credited to the assignee only for code the assignee wrote (5 tasks finished by a
  teammate count as zero). Four tasks whose only evidence was a comment or a document cannot be judged from source and are excluded from
  scoring (listed in the manifest as `verifiable: false`).
- **Withheld**: the board status (Done, Partially Done) is not shown to any experiment, because the simulator derives it from the truth.
- **Split**: student-disjoint, fixed in the manifest: 20 development students (84 verifiable tasks), 30 held-out students (131).
  Prompts and the rating rule may be adjusted on the development set only; the held-out set is scored once per experiment (plus the repeat runs below).
- **Model and settings**: one Groq model for the assessor in every experiment (`GROQ_MODEL`, default `openai/gpt-oss-120b`), temperature 0, reasoning effort
  low, the same rubric word for word (`rf_bench/rubric.py`, hash printed in every result), no worked examples. The critic of Experiment 3 uses a
  different model family (`qwen/qwen3.8-27b`).
- **Output and arithmetic**: one verdict per criterion (`met`, `partly`, `not_met`, `cannot_tell`); the task value is the mean of the verdict values
  (1, 0.5, 0, 0), the sprint value the mean over the student's tasks. The model never does the arithmetic.
- **Limits**: the Groq account allows 8,000 tokens per minute, 1,000 requests per day and **200,000 tokens per day per key** for `openai/gpt-oss-120b`
  (five keys: about 1,000,000 tokens a day in all). A request above the per-minute limit is refused by the service; that refusal is a failure of the
  experiment that made it and is counted, not hidden. Reaching the daily limit is not a result: the runner pauses, records nothing for the unfinished
  items and is resumed with the same command after the limit resets.

## The experiments

**Experiment 1, single prompt.** One call per task with the task text, the acceptance criteria and the whole cleaned diff of the task's commits.
Fair footing: it is given the **correct** commit-to-task mapping (the proposal assumes a classifier does this), so a difference comes from
size, not mapping. Two arms, both reported: *as proposed* (the whole diff, no cutting; refused by the service when it exceeds the per-request limit)
and *cut to the limit* (the diff cut at the largest size the account accepts, with a visible marker, so every task gets a rating).

**Experiment 2, agent.** A LangGraph graph run per task: it must find the task's commits itself (no mapping given), then for each criterion
retrieve code with read-only tools scoped to the student (`rf_bench/scope.py`) and give a verdict citing what it read. Budgets of steps and tokens;
a task with too little coverage is marked low confidence.

**Experiment 3, agent plus critic.** The Experiment 2 agent's verdicts and the code it cited go to a second model of a different family, not shown the
agent's task rating. It confirms or challenges each verdict; a challenged verdict is re-read once by the agent. Kept only if it helps (rule below).

## Evaluation (one scorer, `rf_bench/metrics.py`)

Per experiment: agreement with the truth at criterion level (accuracy, precision and recall of "not met"), task level (MAE, RMSE, Pearson,
Spearman, quadratic weighted kappa on 1-5 bands, bias, calibration slope) and sprint level; all of it **by task-size bucket** (<=4k, 4-8k,
8-16k, 16-32k, >32k tokens); failure rate by kind; tokens, calls and seconds per task; repeatability over repeated runs (spread, share of items moving a
band, ICC, MAE of the median run). Intervals are 95% and resample whole students. Failed items are reported two ways: completed items only, and
failures counted as no credit (the fallback a pipeline would produce).

Held-out sample: equal numbers per size bucket (so large tasks are not drowned out), the same items in every experiment. Overall figures are
also reported weighted by the real share of each bucket.

## Decision rules (fixed now)

1. **Best experiment** = lowest task MAE with failures counted as no credit on the held-out sample. If the 95% paired interval of the difference to the next
   one includes 0, the cheaper one (tokens per task) is preferred. The best one is merged into `feature/requirement-fulfillment-sadeesha`; the others stay as the record.
2. **The critic** (Experiment 3) is kept only if its MAE is lower than Experiment 2's with a paired interval that excludes 0 and the gain exceeds the run-to-run
   spread measured for Experiment 2.
3. **The claim "prompting alone is enough"** is stated for each size bucket as supported (Experiment 1 within 0.02 MAE of the agent, or better) or not.
4. Nothing is tuned on the held-out set, and no result is dropped.

## What this does and does not show

- The benchmark is mock data built by the assistant from a simulation; the truth is what the simulation wrote. It tests judgment at real task sizes
  and the student-only tools. It does **not** show accuracy on real student repositories or against human judges, and the filler code is generic.
- The truth for a criterion can be subtle (for example a status code of 400 where the criterion says 409); the benchmark's hand-written deciding lines
  carry that, and they are few lines per task.
- Groq's limits on this account decide what Experiment 1 can send; a result of "fails above N tokens" is partly a statement about the account, and is
  reported as such alongside the model's own window (131,072 tokens).

## Amendment log

| Date | Change | Reason | Post-hoc? |
| --- | --- | --- | --- |
| 2026-10-19 | After the first live smoke tests of the agent (10 development tasks): the agent's actions became native function calls (the model kept making its own built-in call and the service rejected it); action calls reserve 600 tokens instead of 1,200; the search tool falls back to the words of the query when nothing matches exactly; a repeated search is flagged; one retry on the last step. | The first live runs scored near zero because of these interface problems, not because of the model's judgment. | Yes, on the development set only. Every smoke run is kept in `runs/` (`*_v1`, `_v3`, `_v4` are the earlier versions). No held-out item had been run. |
| 2026-10-19 | Sample sizes: development 4 tasks per size bucket (20 tasks; the 10-task smoke runs are a subset and are reused), held-out 8 per bucket (40 tasks), the same items in every experiment. Repeat runs on a subset. | The daily token limit (about 1,000,000 tokens a day for the model) is far below the cost of the planned 60 tasks per experiment (the agent costs about 18,000 tokens per task). The runs are spread over several days. | Yes, decided after seeing the limit and the costs, before any held-out run. |
| 2026-10-19 | A client bug (an organisation id containing letters that matched the daily-quota check) marked the keys as exhausted too early; two development runs of Experiment 1 made under it were discarded and rerun. | The runs recorded quota failures that were not real. | Yes. |
| 2026-10-19 | The daily limit is a token bucket that refills continuously (200,000 tokens a day per key, so about 1,000,000 a day, 42,000 an hour, across five keys), not a reset at a fixed hour. Held-out sampling is staged: 4 tasks per size bucket first (20 tasks), extended to 8 per bucket (40) when the budget allows; the items are nested, so extending only adds items. Comparisons use the items every compared experiment has finished. | The planned 40 tasks per experiment cost about 2,300,000 tokens; 20 tasks cost about 900,000, one day of budget. | Yes, decided after seeing the refill behaviour, before any experiment had finished its held-out items. |


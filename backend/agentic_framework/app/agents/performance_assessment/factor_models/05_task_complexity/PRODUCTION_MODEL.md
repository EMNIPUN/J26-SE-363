# Task Complexity: the model the agent uses

**Entry point:** [evaluate.py](evaluate.py), model card [model/task_complexity_model.json](model/task_complexity_model.json) ([../ml_lib/fit_production.py](../ml_lib/fit_production.py); [../evidence/linear_model.py](../evidence/linear_model.py)).

**Model.** Ridge on the proposal's five features (story points of the task, subtasks, files involved, dependency reach, component breadth) plus the **total story points the student was assigned in the sprint** (`TC_SP_total`).

**Evidence, and its limit.** 144 real student-sprints, student-disjoint 5-fold cross-validation, assistant-written rubric labels: MAE 0.087 (mean predictor 0.145), Pearson 0.78. **All of the signal is the sprint's story points**: the one-feature baseline (story points of the sprint, log) has MAE 0.091 and the full model is not shown to beat it (gain 0.004, 95% interval [-0.001, 0.010]); the proposal's five code-and-board features alone reach Pearson 0.40 and are worse than the baseline. Every result carries a warning saying so.

**Why this matters.** The rater who wrote the labels saw the story points of the sprint, so the relation between the label and story points may reflect how the rubric was applied more than how hard the work was. The code-based measures (files involved, dependency reach, component breadth) add nothing measurable on these 144 records. The other branch's exp04 reports a higher figure (MAE 0.082) with `TC_reach_density` and `RF_tasks_done`; `TC_reach_density` is defined nowhere in the repository, so that model is not reproduced and not used.

**Does not show.** That the factor measures task difficulty independently of how many story points a student was given; agreement with human graders; any benefit of the dependency-reach features.

**Provisional use.** Computable as soon as tasks are assigned (it is a property of the plan and the code before the work), so it carries no minimum number of days.

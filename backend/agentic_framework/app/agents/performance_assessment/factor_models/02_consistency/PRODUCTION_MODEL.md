# Consistency: the model the agent uses

**Entry point:** [evaluate.py](evaluate.py), model card [model/consistency_model.json](model/consistency_model.json) ([../ml_lib/fit_production.py](../ml_lib/fit_production.py); [../evidence/linear_model.py](../evidence/linear_model.py)).

**Model.** Ridge on two features: active-days share (`C_AWR`) and the day of the first commit (`C_first_active_day`). A student with no activity scores 0.

**Evidence it works.** 144 real student-sprints, student-disjoint 5-fold cross-validation, assistant-written rubric labels: MAE 0.058 (mean predictor 0.206, active days alone 0.078), Pearson 0.923, every prediction within one rubric band. Gain over the active-days baseline 0.021 MAE, 95% interval [0.014, 0.027].

**What was changed from the other branch's experiment.** The proposal's four features (`C_AWR`, `C_DC`, `C_LI_norm`, `C_CV_norm`) do **not** beat active days alone (gain -0.001, interval [-0.005, 0.004]). Adding the day of the first commit does (MAE 0.060 with all four, 0.058 with active days and first day). The other branch's exp04 reports a blended ensemble with `C_early_pace` and `C_DC_penalty`; those two features are defined nowhere in the repository, so that model could not be reproduced and is not used.

**Does not show.** Agreement with human graders; that the proposal's late-work and idle-run measures carry any signal beyond active days and the start day in this data (they do not add to it); behaviour for sprints of a length other than 14 days.

**Provisional use.** Needs at least 5 days of the sprint, otherwise "not available" (rhythm cannot be read earlier). Before sprint end the score is flagged provisional with a widened interval.

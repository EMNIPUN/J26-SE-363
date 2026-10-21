This folder contains the Collaboration factor model for analyzing peer code review depth, technical discussion participation, and team interaction follow-through.

## Cleaning (what counts)

Only the student's own reviews and comments on other people's pull requests; text is cleaned of quotes, code, links, mentions, emoji and padding before it is scored; approvals score zero. The shared-file ratio is not used because it depends on teammates.

Code: [cleaning.py](cleaning.py), tests: `python -m unittest discover -s 04_collaboration/tests` from `factor_models/`. How this fits the agent and the training data: [../ARCHITECTURE.md](../ARCHITECTURE.md).

## Score and entry point

[score.py](score.py): equal-weight mean of six measures with an evidence gate (no team review in the sprint gives "not available", not 0); [evaluate.py](evaluate.py): the production entry point used by `com_agent/factor_bridge.py` (takes `evidence/1`; raises `NotEnoughEvidence` when the score is not available so fusion redistributes the weight; feature payloads still go to `simulate.py`). The result carries the six measures, the counts behind them, what was removed, a sensitivity interval (design uncertainty, not a statistical interval) and warnings.

Design and what is claimed: [training/PROTOCOL.md](training/PROTOCOL.md). Comment-substance scorer trained on public data: [training/SUBSTANCE_PROTOCOL.md](training/SUBSTANCE_PROTOCOL.md). Notebooks and results: [training/experiments/](training/experiments/) (`exp01_dataset_analysis`, `exp02_substance_scorer`, `exp03_fixed_score`), start with `exp03_fixed_score/04_FIXED_SCORE_AND_SENSITIVITY.ipynb` (audit: only 8 of 144 real student-sprints can be scored; known weakness: the response-rate measure credits merging one's own pull requests).

Not claimed: accuracy against human collaboration ratings (none exist), that the substance scorer transfers to student comments.

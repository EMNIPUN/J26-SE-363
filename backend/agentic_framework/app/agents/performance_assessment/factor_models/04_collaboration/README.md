This folder contains the Collaboration factor model for analyzing peer code review depth, technical discussion participation, and team interaction follow-through.

## Cleaning (what counts)

Only the student's own reviews and comments on other people's pull requests; text is cleaned of quotes, code, links, mentions, emoji and padding before it is scored; approvals score zero. The shared-file ratio is not used because it depends on teammates.

Code: [cleaning.py](cleaning.py), tests: `python -m unittest discover -s 04_collaboration/tests` from `factor_models/`. How this fits the agent and the training data: [../ARCHITECTURE.md](../ARCHITECTURE.md).

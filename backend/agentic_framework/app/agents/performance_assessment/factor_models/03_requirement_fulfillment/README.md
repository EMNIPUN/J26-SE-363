This folder contains the Requirement Fulfillment factor model for evaluating code diffs against task acceptance criteria using an AST-grounded evaluator-critic pipeline.

## Cleaning (what counts)

`clean_task_diff` builds the diff the judge reads: source files only, comment, blank, moved and commented-out lines removed, cut at 12,000 characters with a marker. Board features are computed in `featurize`; judge rating is 1-4 and work by a teammate is not credited.

Code: [cleaning.py](cleaning.py), tests: `python -m unittest discover -s 03_requirement_fulfillment/tests` from `factor_models/`. How this fits the agent and the training data: [../ARCHITECTURE.md](../ARCHITECTURE.md).

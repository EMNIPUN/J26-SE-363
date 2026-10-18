This folder contains the Behavioral Pattern factor model for classifying student contribution archetypes and computing contextual score adjustments.

## Cleaning (what counts)

No cleaning of its own: it reads the other factors' scores. `validate_inputs` checks ranges and cleaning versions. Thresholds must become fixed numbers before single-student use.

Code: [cleaning.py](cleaning.py), tests: `python -m unittest discover -s 06_behavioral_pattern/tests` from `factor_models/`. How this fits the agent and the training data: [../ARCHITECTURE.md](../ARCHITECTURE.md).

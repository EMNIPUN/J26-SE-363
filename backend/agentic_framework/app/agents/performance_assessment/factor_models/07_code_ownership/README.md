This folder contains the Code Ownership factor model for verifying authentic student code understanding through targeted comprehension question analysis.

## Cleaning (what counts)

Blame (`-w`, format-only commits ignored) counted on real source lines only; survival, primary-owner share and quiz-candidate files from an `ownership` summary; `snippet_candidates` selects real logic for the quiz.

Code: [cleaning.py](cleaning.py), tests: `python -m unittest discover -s 07_code_ownership/tests` from `factor_models/`. How this fits the agent and the training data: [../ARCHITECTURE.md](../ARCHITECTURE.md).

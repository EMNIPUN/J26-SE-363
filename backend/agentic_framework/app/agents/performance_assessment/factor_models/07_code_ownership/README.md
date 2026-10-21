This folder contains the Code Ownership factor (proposal 3.1.8): it checks whether a student understands the code they are credited with. KO = (R - 1) / 4, where R is a 1-5 comprehension rating of the student's answer to a question about their own code.

## How it works (files in this folder)

1. **Choose the code** ([cleaning.py](cleaning.py), `snippet_candidates`): real logic only (at least 8 counted lines, no getters, setters or shells) from files where the student holds surviving counted lines. Passive features (survival, primary-owner share) are reported as context and are not part of KO.
2. **Generate the question** ([quiz.py](quiz.py), [questions.py](questions.py)): for Python the syntax tree gives the facts (guards, handlers, early returns, loops, returns) and a template builds a structural question plus the reference criteria. The choice of function and question is a hash of student and sprint, so it is repeatable. Other languages get one general question and a warning (no parser yet).
3. **Rate the answer** ([score.py](score.py), [ko_features.py](ko_features.py), [embedder.py](embedder.py), [ko_blocks.py](ko_blocks.py)): deterministic guards first (empty, repeats the question, copies the code, mentions nothing from this code, one-word padding: rated 1 without the model); then a frozen CodeBERT encoder embeds answer, question, code and reference; the trained head (SVR on answer embedding + similarities + 12 hand-built features, in `model/`) predicts the rating; KO = (R - 1) / 4, with a band from the development residuals.
4. **Entry point** ([evaluate.py](evaluate.py)): `generate_quiz(payload)` and `evaluate(payload)`. It raises `NotEnoughEvidence` ("not available", the weight is redistributed, never a guessed score) when there is no answer yet, when torch, scikit-learn or the encoder weights are missing, or when the code is not Python (the scorer is trained and tested on Python only; `allow_unvalidated_language` overrides this and adds a warning). A quiz timeout is a real zero. The 48-hour window, the extension cap of 0.50 and the double timeout are handled by the agent's quiz node (`com_agent/nodes/active_quiz_node.py`), which calls this folder through the bridge.

Needs in the agent's environment: `torch`, `transformers`, `scikit-learn`, `joblib`, `numpy`, and the CodeBERT weights (about 500 MB, downloaded from the hub on first use or placed in `KO_ENCODER_DIR`).

Tests: `python -m unittest discover -s 07_code_ownership/tests` from `factor_models/`.

## What is known about it (training/experiments/exp01_baseline_pipeline, protocol in training/PROTOCOL.md)

- **Data:** 36 real standard-library functions, 216 answers **written by the assistant** at five rubric levels (an independent blind rating by a separate model instance agrees at QWK 0.93). No student data, no human ratings.
- **Model choice:** 144 combinations (3 encoders x 8 feature sets x 6 heads) tuned without selection bias. CodeBERT + similarities + hand-built features + SVR beat the best ridge (5 of 5 folds) and the best hand-feature model (5 of 5 folds). Development MAE 0.161, Spearman 0.81 (baseline: mean 0.319, answer length 0.309).
- **Final test (6 held-out functions, once):** MAE 0.137 (0.10 to 0.17), Spearman 0.88, QWK 0.84, ICC 0.85.
- **Gaming:** the first robustness run failed the pre-set criteria for an answer written for another function (median predicted rating 3.69, needed at most 2.0), generic filler (3.05) and padding (2.82); two deterministic guards were added afterwards (see the protocol and notebook 7 for the numbers before and after).
- **Not claimed:** agreement with human graders on real student answers, results on JavaScript or Java, or robustness against attacks not in the test set. The proposal's validation needs real answers from the live quiz rated by humans.

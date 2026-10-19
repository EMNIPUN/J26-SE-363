**Result against the protocol's criteria (fixed before training).**

| Criterion | Value | Verdict |
|---|---|---|
| External AUC, OpenDev to RevHelper (scored once) | 0.557 (95% 0.522 to 0.590) | **not met** (minimum 0.70) |
| Grouped cross-validation AUC within OpenDev | 0.701 (0.672 to 0.729) | minimum met |
| Beats TF-IDF + logistic (paired interval) | -0.012 (-0.042 to +0.015) | **not met** |
| Guard layer: approvals and one-word texts score 0 | all | target met |

**What was chosen.** Of the three frozen encoders, RoBERTa (mean pooling) was best (pooled AUC 0.70), MiniLM and mpnet were about 0.69. Adding length, code and question flags did not help. The rule for a complex head was **not** met: Random Forest on RoBERTa gained +0.004 AUC (interval -0.009 to +0.018), so logistic regression stays as the head. The final configuration is RoBERTa embeddings with logistic regression (C = 32). The reverse direction (train RevHelper, test OpenDev, same configuration) gave 0.489, no signal.

**What it means.** By the protocol's own criteria, the encoder-based scorer is **not shown to work** and does not beat the much simpler TF-IDF baseline. It reproduces about the same weak signal within OpenDev (about 0.70) and does not carry over to the other public set. So the proposal's frozen-encoder-plus-head design is not supported by these data. The likely reasons, which I did not test, are that the two datasets define "useful" differently and that usefulness depends on the code the comment refers to, which the text does not contain. A better encoder would probably not fix that. The optional fine-tuning experiment (protocol step 9) was not run, since a bigger model would not change the label problem.

**Decision.** The rule-based substance score in `cleaning.py` stays as the stand-in for the substance measures. The trained scorer is saved (`results/substance_scorer.joblib`) for comparison and is not recommended for use.

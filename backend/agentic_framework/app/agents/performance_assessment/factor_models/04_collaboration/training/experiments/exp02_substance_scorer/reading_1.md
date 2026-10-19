**What the baselines show.**
- Within OpenDev (grouped by code change) the best baseline is TF-IDF with logistic regression at AUC 0.71 (95% interval 0.68 to 0.75). Comment length alone and the rule score in `cleaning.py` reach about 0.65. The constant model is at 0.47, which is what no signal looks like once the folds' differing useful shares are accounted for.
- **Across the two public sets every baseline collapses to about 0.5 or worse.** Length alone scores 0.47 when trained on OpenDev and tested on RevHelper and **0.35** the other way round, so the length-to-usefulness relation has the opposite sign in the two sets. The sets label "useful" differently: OpenDev is 82% useful and includes very short comments ("ditto", "nit:", "Not needed.") that the author acted on; RevHelper is 60% useful and its useful comments are longer.
- The labels mean "the author acted on this comment", which depends on the code the comment was about. A text-only scorer cannot see that code, so the ceiling for any text-only model is low, and it is set mostly by how each dataset was labeled.

**The guard layer costs agreement with the public labels.** It scores approvals, texts under 3 words and padding as 0. That affects 19.5% of OpenDev comments, of which 70% are labeled useful (6.4% of RevHelper, 65% useful). For student comments this is the right design, because it blocks comment spam, but it means the public labels can never reward a short "ditto".

**What this does not show.** Nothing here measures how well any scorer works on student comments.

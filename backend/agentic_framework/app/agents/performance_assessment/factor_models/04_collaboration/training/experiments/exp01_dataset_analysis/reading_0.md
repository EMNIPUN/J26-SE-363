**Verdict: the ratings are good, but this data is not suitable for training a text-only scorer that has to work on human-written comments. A model trained on it would look fine on its own cross-validation and would not transfer. I would not expect better results than before.**

**What is good.**
- 2,775 rated comments (1,403 rated 1 for relevance, 3% rated 5), so the scale is used and there is something to learn.
- The ratings are reliable: two annotators agree with ICC 0.80 on relevance, comprehensiveness and conciseness (exact agreement 68-74%, within one point 89-94%, on 264 doubly rated comments). A perfect predictor could reach about 0.9 correlation with a single rater, so the labels are not the limit.
- Relevance, comprehensiveness and conciseness correlate 0.86-0.96, so one number (relevance) is enough.

**What is wrong for our purpose.**
1. **The comments are 90% model-written (2,485 of 2,775; 290 are human).** The writer alone explains 25% of the variance of relevance, and a plain text model can tell human from model comments with AUC 0.88. A scorer can earn credit by recognising the writer's style.
2. **Length bias.** In the model-written comments, longer is rated better (Spearman 0.32 with relevance); in the human-written ones it is weak (0.14). A scorer trained mostly on model-written text learns "longer is better".
3. **The pilot shows it does not transfer.** Ridge on text, five folds grouped by diff, Spearman with relevance: TF-IDF 0.48, MiniLM 0.37, length alone 0.29 over all comments, but **0.06 to 0.14 on the human-written ones**, and 0.08 to 0.14 when trained on model-written comments and tested on human-written ones. A learning curve on the 290 human-written comments alone stays near 0.05-0.10 up to 200 training comments, so more of them would not obviously fix it.
4. **Relevance is judged against the code change.** The raters saw the diff and the claims about it. Text alone cannot say whether a comment is relevant to code it does not contain.

**What would make a dataset suitable.** Mostly human-written comments, with the code change as an input (a model that reads comment and diff together), or labels that depend on the comment itself (specific, explains why, gives a fix) and not on the diff.

**Use of this data.** The 290 human-written, doubly checked comments are still a valid small test set to compare scorers, and the human-agreement figures (ICC 0.80) are a useful ceiling to cite.

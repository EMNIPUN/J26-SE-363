**What the data is.** 36 real Python standard-library functions, one generated question each, 216 answers written by the assistant at five rubric levels (42 / 43 / 41 / 36 / 54 answers at levels 1 to 5). No student wrote any of it and no human rated it.

**The length confound was checked and reduced.** The first version had Spearman 0.83 between answer length and level; after adding short correct and long weak answers it is 0.50 (0.34 to 0.73 inside the question types). Length still carries real signal, as it does in human grading, and the baselines in notebook 2 show it.

**Rater agreement.** A separate Claude instance that saw only a shuffled sheet without levels agreed with the written levels at QWK 0.93, Spearman 0.93, 73% exactly and 98% within one level. Only 4 answers differ by two levels (all four are short "restates the return statement" answers the independent rater scored 4 and the written level 2). Both are model judgements with correlated habits: the agreement shows the levels are readable, not that humans would agree.

**Splits.** 30 development functions (178 answers) in 5 folds of 6 functions (one of each question type per fold), and 6 final-test functions (38 answers, one per question type), fixed by hash.

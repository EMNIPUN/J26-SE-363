# agent: dev (openai/gpt-oss-120b)

Tasks 10, completed 10, failure rate 0.000. Benchmark 8e0b51c7d4a8, code e39d42e.

| view | n | MAE | RMSE | bias | Pearson | Spearman | weighted kappa | within 1 band |
|---|---|---|---|---|---|---|---|---|
| task, completed only | 10 | 0.350 | 0.417 | -0.350 | 0.661 | 0.744 | 0.247 | 0.400 |
| task, failures as no credit | 10 | 0.350 | 0.417 | -0.350 | 0.661 | 0.744 | 0.247 | 0.400 |
| sprint | 9 | 0.370 | 0.429 | -0.370 | 0.604 | 0.603 | 0.186 | 0.444 |

Task MAE (failures as no credit) 0.350 (0.204 to 0.483); completed only 0.350 (0.204 to 0.483); criterion accuracy 0.645 (0.519 to 0.783); Pearson 0.661 (0.346 to 1.000).
Real-share-weighted task MAE (failures as no credit): 0.365.

By task size (tokens of the cleaned diff):

| bucket | tasks | failure rate | MAE completed | MAE no credit | criterion acc completed | criterion acc all |
|---|---|---|---|---|---|---|
| <=4k | 2 | 0.000 | 0.583 | 0.583 | 0.400 | 0.400 |
| 4-8k | 2 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 |
| 8-16k | 2 | 0.000 | 0.333 | 0.333 | 0.667 | 0.667 |
| 16-32k | 2 | 0.000 | 0.250 | 0.250 | 0.750 | 0.750 |
| >32k | 2 | 0.000 | 0.583 | 0.583 | 0.429 | 0.429 |

Criterion verdicts (completed): accuracy 0.645, not-met precision 0.353, recall 1.000, shares {'met': 0.45161290322580644, 'partly': 0.0, 'not_met': 0.3548387096774194, 'cannot_tell': 0.1935483870967742}.
Cost per task: 17872 tokens, 14.5 calls, 153.5 s; failures by kind {}.

# agent: dev (openai/gpt-oss-120b)

Tasks 10, completed 10, failure rate 0.000. Benchmark 8e0b51c7d4a8, code d88c279.

| view | n | MAE | RMSE | bias | Pearson | Spearman | weighted kappa | within 1 band |
|---|---|---|---|---|---|---|---|---|
| task, completed only | 10 | 0.808 | 0.834 | -0.808 | n/a | n/a | 0.000 | 0.000 |
| task, failures as no credit | 10 | 0.808 | 0.834 | -0.808 | n/a | n/a | 0.000 | 0.000 |
| sprint | 9 | 0.806 | 0.830 | -0.806 | n/a | n/a | 0.000 | 0.000 |

Task MAE (failures as no credit) 0.808 (0.713 to 0.898); completed only 0.808 (0.713 to 0.898); criterion accuracy 0.194 (0.120 to 0.261); Pearson n/a (n/a to n/a).
Real-share-weighted task MAE (failures as no credit): 0.779.

By task size (tokens of the cleaned diff):

| bucket | tasks | failure rate | MAE completed | MAE no credit | criterion acc completed | criterion acc all |
|---|---|---|---|---|---|---|
| <=4k | 2 | 0.000 | 0.750 | 0.750 | 0.200 | 0.200 |
| 4-8k | 2 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| 8-16k | 2 | 0.000 | 0.667 | 0.667 | 0.333 | 0.333 |
| 16-32k | 2 | 0.000 | 0.625 | 0.625 | 0.375 | 0.375 |
| >32k | 2 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 |

Criterion verdicts (completed): accuracy 0.194, not-met precision 0.194, recall 1.000, shares {'met': 0.0, 'partly': 0.0, 'not_met': 0.06451612903225806, 'cannot_tell': 0.9354838709677419}.
Cost per task: 2030 tokens, 13.4 calls, 229.9 s; failures by kind {}.

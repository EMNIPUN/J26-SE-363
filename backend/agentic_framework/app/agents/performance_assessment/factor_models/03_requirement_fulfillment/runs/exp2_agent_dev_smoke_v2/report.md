# agent: dev (openai/gpt-oss-120b)

Tasks 10, completed 0, failure rate 1.000. Benchmark 8e0b51c7d4a8, code d88c279.

| view | n | MAE | RMSE | bias | Pearson | Spearman | weighted kappa | within 1 band |
|---|---|---|---|---|---|---|---|---|
| task, completed only | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| task, failures as no credit | 10 | 0.808 | 0.834 | -0.808 | n/a | n/a | 0.000 | 0.000 |
| sprint | 9 | 0.806 | 0.830 | -0.806 | n/a | n/a | 0.000 | 0.000 |

Task MAE (failures as no credit) 0.808 (0.713 to 0.898); completed only n/a (n/a to n/a); criterion accuracy 0.194 (0.120 to 0.261); Pearson n/a (n/a to n/a).
Real-share-weighted task MAE (failures as no credit): 0.779.

By task size (tokens of the cleaned diff):

| bucket | tasks | failure rate | MAE completed | MAE no credit | criterion acc completed | criterion acc all |
|---|---|---|---|---|---|---|
| <=4k | 2 | 1.000 | n/a | 0.750 | n/a | 0.200 |
| 4-8k | 2 | 1.000 | n/a | 1.000 | n/a | 0.000 |
| 8-16k | 2 | 1.000 | n/a | 0.667 | n/a | 0.333 |
| 16-32k | 2 | 1.000 | n/a | 0.625 | n/a | 0.375 |
| >32k | 2 | 1.000 | n/a | 1.000 | n/a | 0.000 |

Criterion verdicts (completed): accuracy n/a, not-met precision n/a, recall n/a, shares None.
Cost per task: 1671 tokens, 6.1 calls, 50.8 s; failures by kind {'bad_request': 10}.

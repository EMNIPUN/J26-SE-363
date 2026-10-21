# agent_critic: dev (openai/gpt-oss-120b)

Tasks 10, completed 10, failure rate 0.000. Benchmark 8e0b51c7d4a8, code 19f84b5.

| view | n | MAE | RMSE | bias | Pearson | Spearman | weighted kappa | within 1 band |
|---|---|---|---|---|---|---|---|---|
| task, completed only | 10 | 0.342 | 0.414 | -0.342 | 0.662 | 0.647 | 0.286 | 0.500 |
| task, failures as no credit | 10 | 0.342 | 0.414 | -0.342 | 0.662 | 0.647 | 0.286 | 0.500 |
| sprint | 9 | 0.361 | 0.426 | -0.361 | 0.604 | 0.558 | 0.235 | 0.556 |

Task MAE (failures as no credit) 0.342 (0.204 to 0.477); completed only 0.342 (0.204 to 0.477); criterion accuracy 0.645 (0.519 to 0.786); Pearson 0.662 (0.343 to 1.000).
Real-share-weighted task MAE (failures as no credit): 0.327.

By task size (tokens of the cleaned diff):

| bucket | tasks | failure rate | MAE completed | MAE no credit | criterion acc completed | criterion acc all |
|---|---|---|---|---|---|---|
| <=4k | 2 | 0.000 | 0.417 | 0.417 | 0.600 | 0.600 |
| 4-8k | 2 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 |
| 8-16k | 2 | 0.000 | 0.333 | 0.333 | 0.667 | 0.667 |
| 16-32k | 2 | 0.000 | 0.250 | 0.250 | 0.750 | 0.750 |
| >32k | 2 | 0.000 | 0.708 | 0.708 | 0.286 | 0.286 |

Criterion verdicts (completed): accuracy 0.645, not-met precision 0.353, recall 1.000, shares {'met': 0.45161290322580644, 'partly': 0.0, 'not_met': 0.25806451612903225, 'cannot_tell': 0.2903225806451613}.
Cost per task: 19434 tokens, 16.0 calls, 177.7 s; failures by kind {}.

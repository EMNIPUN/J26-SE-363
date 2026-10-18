# agent: dev (openai/gpt-oss-120b)

Tasks 10, completed 10, failure rate 0.000. Benchmark 8e0b51c7d4a8, code 24e7e8f.

| view | n | MAE | RMSE | bias | Pearson | Spearman | weighted kappa | within 1 band |
|---|---|---|---|---|---|---|---|---|
| task, completed only | 10 | 0.492 | 0.558 | -0.492 | 0.567 | 0.582 | 0.159 | 0.300 |
| task, failures as no credit | 10 | 0.492 | 0.558 | -0.492 | 0.567 | 0.582 | 0.159 | 0.300 |
| sprint | 9 | 0.472 | 0.545 | -0.472 | 0.547 | 0.523 | 0.199 | 0.333 |

Task MAE (failures as no credit) 0.492 (0.271 to 0.642); completed only 0.492 (0.271 to 0.642); criterion accuracy 0.484 (0.333 to 0.708); Pearson 0.567 (0.289 to 0.855).
Real-share-weighted task MAE (failures as no credit): 0.463.

By task size (tokens of the cleaned diff):

| bucket | tasks | failure rate | MAE completed | MAE no credit | criterion acc completed | criterion acc all |
|---|---|---|---|---|---|---|
| <=4k | 2 | 0.000 | 0.417 | 0.417 | 0.600 | 0.600 |
| 4-8k | 2 | 0.000 | 0.333 | 0.333 | 0.600 | 0.600 |
| 8-16k | 2 | 0.000 | 0.500 | 0.500 | 0.500 | 0.500 |
| 16-32k | 2 | 0.000 | 0.375 | 0.375 | 0.625 | 0.625 |
| >32k | 2 | 0.000 | 0.833 | 0.833 | 0.143 | 0.143 |

Criterion verdicts (completed): accuracy 0.484, not-met precision 0.273, recall 1.000, shares {'met': 0.2903225806451613, 'partly': 0.0, 'not_met': 0.3225806451612903, 'cannot_tell': 0.3870967741935484}.
Cost per task: 13578 tokens, 12.7 calls, 212.5 s; failures by kind {}.

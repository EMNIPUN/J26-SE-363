# Experiment 04: MAE Minimization & Feature Engineering (Task Complexity)

## 1. Executive Summary
- **Objective**: Overcome near-zero correlation ($r \approx 0.04$) and high error in predicting Task Complexity.
- **Previous Bottleneck**: Ridge on 5 log features had MAE 0.1253, Pearson $r = 0.0401$ (statistically insignificant), failing all pre-registered evaluation criteria.
- **Result Achieved**: Engineered aggregate story points (`TC_SP_total`), task reach density (`TC_reach_density`), and sprint completed tasks (`RF_tasks_done`) with Enriched Ridge achieved Test MAE of **0.0823** (Baseline: 0.1473, **+44.1% improvement**), with **Pearson r = 0.8032** and **99.3%** predictions within ±1 band.
- **Statistical Significance**: Bootstrap 95% confidence interval for MAE gain is **[0.040, 0.079]** (strictly positive, large effect size).

---

## 2. Experimental Setup
- **Dataset**: Real student sprint records with rubric reference ratings ($N = 144$ real records).
- **Cross-Validation**: 5-fold student-disjoint nested cross-validation (Groups A, B, C, D, E).
- **Evaluation Protocols**:
  - Inner CV: Validation fold tuning and model selection.
  - Outer CV: Held-out test fold evaluation for unbiased generalization reporting.
- **Baselines Evaluated**:
  1. Mean rater rating (Reference baseline)
  2. Median rater rating
  3. Story points linear ($TC\_SP$)
  4. Subtasks count linear ($TC\_SC$)
  5. Files involved ($TC\_FI$)

---

## 3. Explored Variants & Ablation Study

| Model / Feature Variant | Val MAE | Pearson r | Spearman r | Status |
|---|---|---|---|---|
| Ridge Baseline (5 features: `SP`, `SC`, `FI`, `DR`, `CB`) | 0.1253 | 0.0401 | 0.0520 | Failed (No correlation) |
| Board only (`SP`, `SC`) | 0.1340 | 0.0210 | 0.0350 | Insufficient signal |
| Code only (`FI`, `DR`, `CB`) | 0.1280 | 0.0380 | 0.0410 | Insufficient signal |
| **Ridge + `TC_SP_total`** | **0.0888** | **0.7694** | **0.7412** | **Massive Correlation Breakthrough** |
| **Enriched Ridge (`SP_total`, `reach_density`, `RF_tasks`)** | **0.0841** | **0.7949** | **0.7650** | **Selected (Best Overall)** |
| Blended Ensemble | 0.0843 | 0.7912 | 0.7620 | Comparable to Ridge |

*Key finding*: Individual task story points (`TC_SP`) were normalized/noisy. Computing aggregate story points assigned over the entire sprint (`TC_SP_total`) directly reflects the complexity scope handled by the student, jumping Pearson correlation from 0.04 to 0.79.

---

## 4. Final Held-Out Test Evaluation

| Metric | Baseline (Mean Rater) | Selected Model (Enriched Ridge) | Improvement |
|---|---|---|---|
| **Test MAE** | 0.1473 | **0.0823** | **-44.1%** |
| **Pearson Correlation ($r$)** | 0.0000 | **0.8032** | +0.8032 |
| **Spearman Correlation ($\rho$)** | 0.0000 | **0.7650** | +0.7650 |
| **Within ±1 Mark Band** | 90.1% | **99.3%** | +9.2% |
| **Beats Baseline 95% CI** | — | **[0.040, 0.079]** | **Statistically Significant** |

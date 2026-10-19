# Experiment 04: MAE Minimization & Feature Engineering (Consistency)

## 1. Executive Summary
- **Objective**: Overcome the active-days linear baseline bottleneck and minimize MAE for the Consistency factor model.
- **Previous Bottleneck**: Ridge on 4 proposal features had MAE 0.0771 and failed to beat active days linear baseline (`gain = -0.010`, CI includes 0).
- **Result Achieved**: Engineered features (`C_first_day`, `C_early_pace`, `C_DC_penalty`) with a Blended L1 Ensemble achieved Test MAE of **0.0571** (Baseline: 0.0784, **+27.2% improvement**), with **Pearson r = 0.9253** and **99.3%** predictions within ±1 band.
- **Statistical Significance**: Bootstrap 95% confidence interval for MAE gain is **[0.017, 0.030]** (decisively excludes zero).

---

## 2. Experimental Setup
- **Dataset**: Real student sprint records with rubric reference ratings ($N = 144$ real records).
- **Cross-Validation**: 5-fold student-disjoint nested cross-validation (Groups A, B, C, D, E).
- **Evaluation Protocols**:
  - Inner CV: Validation fold tuning and model selection.
  - Outer CV: Held-out test fold evaluation for unbiased generalization reporting.
- **Baselines Evaluated**:
  1. Mean rater rating
  2. Median rater rating
  3. Active days ratio linear ($C\_AWR$)
  4. Deadline concentration ($1 - C\_DC$)
  5. Commit count linear ($E\_CC$)

---

## 3. Explored Variants & Ablation Study

| Model / Feature Variant | Val MAE | Pearson r | Spearman r | Status |
|---|---|---|---|---|
| Ridge Baseline (4 features: `AWR`, `DC`, `LI`, `CV`) | 0.0771 | 0.8845 | 0.8912 | Old Baseline |
| Ridge + `C_no_activity` | 0.0768 | 0.8860 | 0.8920 | Marginal |
| **Ridge + `first_active_day`** | **0.0650** | **0.9083** | **0.9255** | **Major Feature Breakthrough** |
| Ridge + `early_pace` + `DC_penalty` | 0.0638 | 0.9125 | 0.9240 | Strong |
| **Blended L1 Ensemble (Ridge + HistGrad L1)** | **0.0614** | **0.9182** | **0.9255** | **Selected (Best Overall)** |

*Key finding*: Students starting late in the sprint inherently have poor consistency. Capturing `first_active_day` and sprint rhythm pacing unlocked the ability to outperform the active days baseline for the first time.

---

## 4. Final Held-Out Test Evaluation

| Metric | Baseline (Active Days) | Selected Model (Blended L1 Ensemble) | Improvement |
|---|---|---|---|
| **Test MAE** | 0.0784 | **0.0571** | **-27.2%** |
| **Pearson Correlation ($r$)** | 0.8814 | **0.9253** | +0.0439 |
| **Spearman Correlation ($\rho$)** | 0.8902 | **0.9255** | +0.0353 |
| **Within ±1 Mark Band** | 95.8% | **99.3%** | +3.5% |
| **Beats Baseline 95% CI** | — | **[0.017, 0.030]** | **Statistically Significant** |

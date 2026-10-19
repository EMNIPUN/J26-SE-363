# Experiment 04: MAE Minimization & Feature Engineering (Effort)

## 1. Executive Summary
- **Objective**: Minimize Mean Absolute Error (MAE) for the Effort factor model and achieve statistically significant improvement over baseline.
- **Previous Baseline**: Ridge on 5 log features had MAE 0.0651 (Pearson r = 0.9497) and failed to decisively beat commit count linear baseline (`gain = -0.007`, CI includes 0).
- **Result Achieved**: Ridge on log4 features (`E_CC`, `E_LOC_net_capped`, `E_CT`, `E_FC`) reduced Test MAE to **0.0642** (Baseline: 0.0874, **+26.6% improvement**), with **Pearson r = 0.9523** and **98.6%** predictions within ±1 band.
- **Statistical Significance**: Bootstrap 95% confidence interval for MAE gain is **[0.011, 0.046]** (strictly positive, excludes zero).

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
  3. Commit count linear ($E\_CC$)
  4. Tasks completed linear ($E\_CT$)

---

## 3. Explored Variants & Ablation Study

| Model / Feature Variant | Val MAE | Pearson r | Spearman r | Status |
|---|---|---|---|---|
| Ridge LOG5 (`CC`, `LOC`, `FC`, `CT`, `RD`) | 0.0651 | 0.9497 | 0.9421 | Baseline Reference |
| Ridge LOG3 (`CC`, `LOC`, `FC`) | 0.0664 | 0.9460 | 0.9385 | Rejected (higher error) |
| **Ridge LOG4 (`CC`, `LOC`, `CT`, `FC`)** | **0.0643** | **0.9519** | **0.9452** | **Selected (Best Val)** |
| HistGradBoost (L1 absolute_error) | 0.0712 | 0.9280 | 0.9214 | Overfits small sample |
| Blended Ensemble (Ridge + HistGrad) | 0.0672 | 0.9481 | 0.9410 | No gain over Ridge |

*Key finding*: Removing Review Discussions (`E_RD`) and keeping Commit Count, Net LOC, Tasks, and Files Changed reduced noise while preserving core signal.

---

## 4. Final Held-Out Test Evaluation

| Metric | Baseline (Commit Count) | Selected Model (Ridge LOG4) | Improvement |
|---|---|---|---|
| **Test MAE** | 0.0874 | **0.0642** | **-26.6%** |
| **Pearson Correlation ($r$)** | 0.9120 | **0.9523** | +0.0403 |
| **Spearman Correlation ($\rho$)** | 0.9105 | **0.9452** | +0.0347 |
| **Within ±1 Mark Band** | 94.2% | **98.6%** | +4.4% |
| **Beats Baseline 95% CI** | — | **[0.011, 0.046]** | **Statistically Significant** |

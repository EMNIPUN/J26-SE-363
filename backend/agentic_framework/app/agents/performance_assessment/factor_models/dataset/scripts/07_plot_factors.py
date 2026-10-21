"""Step 7: one analysis sheet per factor, from final_dataset.csv.

Each sheet (analysis/<factor>.png) has: feature distributions (real vs synthetic), the factor
score distribution, each feature against the score, the score by behaviour profile, a feature
correlation heatmap, and the 20 rated anchors (rater's mark vs the model's score with its 90%
interval). analysis/overview.png covers the final mark and the fusion.

    python scripts/07_plot_factors.py
"""

import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from identity import DATASET

OUT = DATASET / "analysis"
REAL, SYN = "#2b6cb0", "#dd6b20"
FACTORS = {
    "E": ("Effort", ["E_CC", "E_LOC_net_capped", "E_FC", "E_CT", "E_RD"], ["E_test_lines"]),
    "C": ("Consistency", ["C_AWR", "C_DC", "C_LI_norm", "C_CV_norm"], ["C_first_active_day"]),
    "RF": ("Requirement fulfilment", ["RF_llm_score", "RF_completion_rate", "RF_ac_ratio", "RF_untracked_ratio"], ["RF_tasks_assigned"]),
    "Co": ("Collaboration", ["Co_PCount", "Co_CCount", "Co_IR", "Co_shared_file_ratio", "Co_prs_merged_for_others", "Co_prs_opened"], []),
    "TC": ("Task complexity", ["TC_SP", "TC_SC", "TC_FI", "TC_DR", "TC_CB"], ["TC_SP_total"]),
    "KO": ("Code ownership", ["KO_survival", "KO_primary_owner_share", "KO_snippet_candidates", "KO_lines_added_code"], []),
}
SKEWED = {"E_CC", "E_LOC_net_capped", "E_FC", "E_RD", "Co_PCount", "Co_CCount", "Co_prs_merged_for_others", "Co_prs_opened",
          "TC_FI", "TC_DR", "TC_CB", "KO_snippet_candidates", "KO_lines_added_code", "E_test_lines"}
SHORT = {"free_rider": "free rider", "reviewer_coordinator": "reviewer", "no_specific_pattern": "no pattern",
         "last_minute_rusher": "last-minute", "burst_worker": "burst", "consistent_deep_contributor": "consistent"}
PROFILE_ORDER = ["free_rider", "reviewer_coordinator", "no_specific_pattern", "last_minute_rusher", "burst_worker", "consistent_deep_contributor"]


def sym(x):
    return np.sign(x) * np.log1p(np.abs(x))


def transform(df, col):
    return sym(df[col]) if col in SKEWED else df[col]


def label(col):
    return ("log " if col in SKEWED else "") + col


def factor_sheet(df, key, title, features, extras):
    score = f"{key}_score"
    lo, hi = f"{key}_score_lo", f"{key}_score_hi"
    real, syn = df[df.source == "real"], df[df.source == "synthetic"]
    anchors = df[df.in_ground_truth == 1].sort_values(f"GT_{key}")
    n = len(features)
    cols = 3
    rows = 3 + math.ceil(n / cols)
    fig = plt.figure(figsize=(17, 3.9 * rows), layout="constrained")
    gs = fig.add_gridspec(rows, cols)
    fig.suptitle(f"{title} ({key}): {len(real)} real and {len(syn)} synthetic records, {len(anchors)} rated", fontsize=15)

    # row 1: score distribution, by profile, anchors
    ax = fig.add_subplot(gs[0, 0])
    bins = np.linspace(0, 1, 21)
    ax.hist(real[score], bins=bins, color=REAL, alpha=0.75, label=f"real (n={len(real)})", density=True)
    ax.hist(syn[score], bins=bins, color=SYN, alpha=0.5, label=f"synthetic (n={len(syn)})", density=True)
    ax.set(title=f"{key} score distribution", xlabel="score (0-1)", ylabel="density")
    ax.legend(fontsize=8)

    ax = fig.add_subplot(gs[0, 1])
    present = [p for p in PROFILE_ORDER if p in set(syn.profile_or_parent) | set(real.BP_pattern)]
    long = pd.concat([
        pd.DataFrame({"profile": syn.profile_or_parent.map(SHORT), "score": syn[score], "source": "synthetic"}),
        pd.DataFrame({"profile": real.BP_pattern.map(SHORT), "score": real[score], "source": "real"}),
    ])
    sns.boxplot(data=long, y="profile", x="score", hue="source", order=[SHORT[p] for p in present], palette={"real": REAL, "synthetic": SYN}, ax=ax, fliersize=2, linewidth=0.9)
    ax.set(title=f"{key} score by behaviour profile", xlabel="score", ylabel="")
    ax.legend(fontsize=8, loc="lower right")

    ax = fig.add_subplot(gs[0, 2])
    ys = np.arange(len(anchors))
    ax.hlines(ys, anchors[lo], anchors[hi], color="#999", lw=3, alpha=0.6, label="model 90% interval")
    ax.scatter(anchors[score], ys, color=REAL, zorder=3, label="model score")
    ax.scatter(anchors[f"GT_{key}"], ys, marker="D", color="#c53030", zorder=4, label="rater")
    ax.set_yticks(ys)
    ax.set_yticklabels(anchors.record_id.str.replace(r"^T\d+-", "", regex=True), fontsize=7)
    ax.set(title="20 rated records: rater vs model (sorted by rater)", xlabel="score")
    ax.legend(fontsize=7, loc="lower right")

    # row 2: score vs fitted/rater, flags, correlation heatmap
    ax = fig.add_subplot(gs[1, 0])
    ax.scatter(anchors[f"GT_{key}"], anchors[score], color=REAL, s=40)
    ax.plot([0, 1], [0, 1], "--", color="#888")
    r = np.corrcoef(anchors[f"GT_{key}"], anchors[score])[0, 1]
    ax.set(title=f"rater vs model score (in-sample r = {r:.2f})", xlabel="rater score", ylabel="model score", xlim=(-0.02, 1.02), ylim=(-0.02, 1.02))

    ax = fig.add_subplot(gs[1, 1])
    width = (df[hi] - df[lo])
    ax.hist(width[df.source == "real"], bins=20, color=REAL, alpha=0.75, label="real", density=True)
    ax.hist(width[df.source == "synthetic"], bins=20, color=SYN, alpha=0.5, label="synthetic", density=True)
    ex = df[f"{key}_extrapolated"]
    ax.set(title=f"uncertainty: 90% interval width ({100 * ex.mean():.0f}% of records flagged extrapolated)", xlabel="interval width (score units)")
    ax.title.set_fontsize(9)
    ax.legend(fontsize=8)

    ax = fig.add_subplot(gs[1, 2])
    cols_h = features + extras + [score]
    frame = pd.DataFrame({c: transform(df, c) for c in cols_h}).apply(pd.to_numeric, errors="coerce")
    frame = frame.loc[:, frame.nunique() > 1]
    corr = frame.corr(method="spearman")
    sns.heatmap(corr, ax=ax, cmap="vlag", center=0, vmin=-1, vmax=1, annot=len(corr) <= 9, fmt=".2f", annot_kws={"size": 7}, cbar_kws={"shrink": 0.7})
    ax.set_title("Spearman correlation (all records)", fontsize=10)
    ax.tick_params(labelsize=7)

    # row 3: feature distributions
    for i, col in enumerate(features):
        ax = fig.add_subplot(gs[2 + i // cols, i % cols])
        a, b = transform(real, col).dropna(), transform(syn, col).dropna()
        if len(a) == 0 and len(b) == 0:
            ax.text(0.5, 0.5, "no data", ha="center")
            continue
        both = pd.concat([a, b])
        bins = np.linspace(both.min(), both.max() if both.max() > both.min() else both.min() + 1, 21)
        ax.hist(a, bins=bins, color=REAL, alpha=0.75, density=True, label=f"real (n={len(a)})")
        ax.hist(b, bins=bins, color=SYN, alpha=0.5, density=True, label=f"synthetic (n={len(b)})")
        zero = (real[col].fillna(0) == 0).mean()
        ax.set(title=f"{label(col)}  ({100 * zero:.0f}% of real = 0 or missing)", xlabel=label(col))
        ax.title.set_fontsize(9)
        ax.legend(fontsize=7)

    # feature vs score
    base = 2 + math.ceil(n / cols)
    for i, col in enumerate(features[:cols]):
        ax = fig.add_subplot(gs[base, i])
        x = transform(df, col)
        ax.scatter(x[df.source == "synthetic"], df.loc[df.source == "synthetic", score], s=8, color=SYN, alpha=0.3, label="synthetic")
        ax.scatter(x[df.source == "real"], df.loc[df.source == "real", score], s=18, color=REAL, alpha=0.8, label="real")
        a = df[df.in_ground_truth == 1]
        ax.scatter(transform(a, col), a[score], s=70, facecolor="none", edgecolor="#c53030", lw=1.5, label="rated")
        rho = pd.concat([x, df[score]], axis=1).dropna().corr(method="spearman").iloc[0, 1]
        ax.set(title=f"{label(col)} vs {key} score (rho = {rho:.2f})", xlabel=label(col), ylabel="score")
        ax.title.set_fontsize(9)
        if i == 0:
            ax.legend(fontsize=7)
    fig.savefig(OUT / f"{title.lower().replace(' ', '_')}.png", dpi=110)
    plt.close(fig)


def overview(df, report):
    real, syn = df[df.source == "real"], df[df.source == "synthetic"]
    fig, axes = plt.subplots(2, 3, figsize=(17, 9.5), layout="constrained")
    fig.suptitle("Final marks and fusion", fontsize=15)
    ax = axes[0, 0]
    bins = np.linspace(0, 100, 21)
    ax.hist(real.final_mark, bins=bins, color=REAL, alpha=0.75, density=True, label="real")
    ax.hist(syn.final_mark, bins=bins, color=SYN, alpha=0.5, density=True, label="synthetic")
    ax.set(title="final mark distribution", xlabel="mark (0-100)")
    ax.legend()

    ax = axes[0, 1]
    present = [p for p in PROFILE_ORDER if p in set(df.BP_pattern)]
    df = df.assign(BP_short=df.BP_pattern.map(SHORT))
    sns.boxplot(data=df, y="BP_short", x="final_mark", hue="source", order=[SHORT[p] for p in present], palette={"real": REAL, "synthetic": SYN}, ax=ax, fliersize=2)
    ax.set(title="final mark by behaviour pattern", ylabel="", xlabel="mark")

    ax = axes[0, 2]
    a = df[df.in_ground_truth == 1]
    ax.scatter(a.GT_overall_mark, a.final_mark, color=REAL, s=50)
    ax.plot([0, 100], [0, 100], "--", color="#888")
    e2e = report["final_mark_loocv"]
    ax.set(title=f"rater overall vs final mark\nleave-one-out MAE {e2e['mae_0_100']}, r {e2e['pearson']}", xlabel="rater overall (0-100)", ylabel="final mark")

    ax = axes[1, 0]
    w = report["fusion"]["weights"]
    ax.barh(list(w), list(w.values()), color=REAL)
    ax.invert_yaxis()
    ax.set(title="learned fusion weights", xlabel="weight")

    ax = axes[1, 1]
    scores = df[[f"{k}_score" for k in FACTORS]].rename(columns=lambda c: c.replace("_score", ""))
    sns.heatmap(scores.corr(method="spearman"), annot=True, fmt=".2f", cmap="vlag", center=0, vmin=-1, vmax=1, ax=ax, cbar_kws={"shrink": 0.7})
    ax.set_title("correlation between factor scores")

    ax = axes[1, 2]
    fac = report["factors"]
    names = list(fac)
    x = np.arange(len(names))
    ax.bar(x - 0.2, [fac[k]["loocv_mae"] for k in names], 0.4, color=REAL, label="model (leave-one-out)")
    ax.bar(x + 0.2, [fac[k]["baseline_mae_predict_mean"] for k in names], 0.4, color="#aaa", label="always predict the mean")
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set(title="error per factor (MAE, 0-1 scale; lower is better)", ylabel="MAE")
    ax.legend(fontsize=8)
    fig.savefig(OUT / "overview.png", dpi=110)
    plt.close(fig)


def main():
    import json

    OUT.mkdir(exist_ok=True)
    df = pd.read_csv(DATASET / "final_dataset.csv", low_memory=False)
    report = json.loads((DATASET / "marks_report.json").read_text())
    sns.set_theme(style="whitegrid", context="paper")
    for key, (title, features, extras) in FACTORS.items():
        factor_sheet(df, key, title, features, extras)
        print("wrote", title)
    overview(df, report)
    print("wrote overview")


if __name__ == "__main__":
    main()

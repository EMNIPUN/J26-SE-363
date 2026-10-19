"""Per-factor configuration for the clean-data retrain (see RETRAIN_PROTOCOL.md). Criteria are the earlier protocols' own."""

from pathlib import Path

from dataclasses import replace

from retrain import REF_CONFIGS, Cfg

FM = Path(__file__).resolve().parents[1]

LOG5 = [("E_CC", "log"), ("E_LOC_net_capped", "log"), ("E_FC", "log"), ("E_CT", "log"), ("E_RD", "log")]
CONS = [("C_AWR", "raw"), ("C_DC", "one_minus"), ("C_LI_norm", "one_minus"), ("C_CV_norm", "one_minus")]
TC5 = [("TC_SP", "raw"), ("TC_SC", "raw"), ("TC_FI", "log"), ("TC_DR", "log"), ("TC_CB", "log")]
COMMON = {"bias": (0.05, 0.03), "slope": ((0.7, 1.3), (0.8, 1.2)), "band_within": (0.85, 0.90), "band_exact": 0.50}


def effort():
    return Cfg(
        key="effort", title="Effort", folder=FM / "01_effort" / "training" / "experiments" / "exp02_clean_retrain", dataset_file="effort_dataset.csv", label="rater_effort", activity="E_CC",
        proposal=LOG5,
        variants={"log5 (proposal)": LOG5, "log3 (commits, lines, files)": LOG5[:3], "log4 (no RD)": LOG5[:4]},
        tuning_variants=["log5 (proposal)", "log3 (commits, lines, files)"],
        baselines=[{"name": "mean", "kind": "mean"}, {"name": "median", "kind": "median"},
                   {"name": "commit count (log, linear)", "kind": "linear", "col": "E_CC", "tf": "log", "zero": True},
                   {"name": "tasks done (linear)", "kind": "linear", "col": "E_CT", "tf": "log", "zero": True},
                   {"name": "ridge (5 proposal features)", "kind": "ridge", "zero": True}],
        reference="commit count (log, linear)", zero_rule=True,
        criteria={**COMMON, "error": ("mae_abs", 0.11, 0.08), "corr": (0.80, 0.90, 0.85), "beat_gain": 0.10, "active": (0.12, 0.10)})


def consistency():
    return Cfg(
        key="consistency", title="Consistency", folder=FM / "02_consistency" / "training" / "experiments" / "exp02_clean_retrain", dataset_file="consistency_dataset.csv", label="rater_consistency",
        activity="E_CC", proposal=CONS,
        variants={"proposal 4": CONS, "proposal 4 + no-activity flag": CONS + [("C_no_activity", "raw")], "3 features (no CV)": CONS[:3],
                  "AWR + 1-DC": CONS[:2]},
        tuning_variants=["proposal 4"],
        baselines=[{"name": "mean", "kind": "mean"}, {"name": "median", "kind": "median"},
                   {"name": "active days (AWR, linear)", "kind": "linear", "col": "C_AWR", "tf": "raw", "zero": True},
                   {"name": "1 - deadline share (linear)", "kind": "linear", "col": "C_DC", "tf": "one_minus", "zero": True},
                   {"name": "commits (log, linear)", "kind": "linear", "col": "E_CC", "tf": "log", "zero": True},
                   {"name": "ridge (4 proposal features)", "kind": "ridge", "zero": True}],
        reference="active days (AWR, linear)", zero_rule=True,
        criteria={**COMMON, "error": ("mae_ratio", 0.50, 0.35), "corr": (0.80, 0.90, 0.85), "beat_gain": 0.10, "active": (0.12, 0.10)})


def task_complexity():
    return Cfg(
        key="task_complexity", title="Task Complexity", folder=FM / "05_task_complexity" / "training" / "experiments" / "exp02_clean_retrain", dataset_file="task_complexity_dataset.csv",
        label="rater_task_complexity", activity="E_CC", proposal=TC5,
        variants={"proposal 5 (log counts)": TC5, "board only (SP, SC)": TC5[:2], "code only (FI, DR, CB)": TC5[2:], "SP, SC, FI": TC5[:3]},
        tuning_variants=["proposal 5 (log counts)"],
        baselines=[{"name": "mean", "kind": "mean"}, {"name": "median", "kind": "median"},
                   {"name": "story points (linear)", "kind": "linear", "col": "TC_SP", "tf": "raw"},
                   {"name": "subtasks (linear)", "kind": "linear", "col": "TC_SC", "tf": "raw"},
                   {"name": "files involved (log, linear)", "kind": "linear", "col": "TC_FI", "tf": "log"},
                   {"name": "ridge (5 proposal features)", "kind": "ridge"}],
        reference="mean", zero_rule=False,
        criteria={"bias": (0.05, 0.03), "slope": ((0.5, 1.5), (0.8, 1.2)), "band_within": (0.85, 0.90), "band_exact": None,
                  "error": ("mae_ratio", 0.80, 0.65), "corr": (0.50, 0.70, 0.70), "beat_gain": 0.20, "active": None})


CONFIGS = {"effort": effort, "consistency": consistency, "task_complexity": task_complexity}


def reference(name):
    """The same configuration on the reference-rating data: every real record rated, simulated records add their own ratings."""
    base = CONFIGS[name]()
    return replace(base, key=f"{base.key}_ref", folder=base.folder.parent / "exp03_reference_retrain", label_configs=list(REF_CONFIGS))


CONFIGS.update({f"{k}_ref": (lambda k=k: reference(k)) for k in list(CONFIGS)})

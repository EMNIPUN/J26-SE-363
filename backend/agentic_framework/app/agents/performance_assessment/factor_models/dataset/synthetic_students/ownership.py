"""Code Ownership values for each simulated student and sprint: (survival, primary-owner share).

Survival is the share of the lines a student added in a sprint that are still in the final version of the project;
primary-owner share is the share of the files they touched where they hold the most surviving lines. Both are read
from the final repository, so:
- earlier sprints have had longer to be rewritten, so their survival is lower than the last sprint's;
- last-minute work is written late and has little time to be replaced, so it survives better;
- reviewers' small changes are most often refactored by others (the real median is 0.39);
- copied or pasted code is replaced or deleted (very low survival, very low ownership);
- work that touches shared files (hubs, models, routes) is owned less cleanly.
Real medians by type (survival / owner): consistent 0.72/0.84, rusher 0.85/0.89, burst 0.67/0.82, no pattern 0.70/0.76,
reviewer 0.39/0.79; 27% of all real records have survival under 0.5. A sprint without code files has no value.
"""

KO = {
    # ---- consistent deep contributors ----
    "SYN-001": {"S1": (0.62, 0.85), "S2": (0.80, 0.90)},
    "SYN-006": {"S1": (0.55, 0.85), "S2": (0.70, 0.85), "S3": (0.88, 0.90)},
    "SYN-011": {"S1": (0.65, 0.90), "S2": (0.70, 0.85), "S3": (0.85, 0.85)},
    "SYN-016": {"S1": (0.50, 0.85), "S2": (0.68, 0.85), "S3": (0.90, 0.80), "S4": (0.85, 0.85)},
    "SYN-026": {"S1": (0.60, 0.92), "S2": (0.62, 0.90), "S3": (0.75, 0.90), "S4": (0.88, 0.92)},
    "SYN-031": {"S1": (0.58, 0.85), "S2": (0.65, 0.85), "S3": (0.72, 0.80), "S4": (0.80, 0.85), "S5": (0.90, 0.85)},
    "SYN-041": {"S1": (0.50, 0.90), "S2": (0.75, 0.90), "S3": (0.85, 0.88)},  # sprint 1 splitting logic rewritten for the rounding fix
    "SYN-046": {"S1": (0.65, 0.88), "S2": (0.70, 0.88), "S3": (0.72, 0.85), "S4": (0.45, 0.70)},  # sprint 4 integration reverted
    # ---- last-minute rushers ----
    "SYN-002": {"S1": (0.70, 0.85), "S2": (0.88, 0.90)},
    "SYN-007": {"S1": (0.75, 0.88), "S2": (0.82, 0.88), "S3": (0.90, 0.90)},
    "SYN-012": {"S1": (0.45, 0.85), "S2": (0.85, 0.88), "S3": (0.90, 0.88)},  # sprint 1 screens redone by teammates after the demo
    "SYN-021": {"S1": (0.70, 0.85), "S2": (0.80, 0.85), "S3": (0.88, 0.88), "S4": (0.92, 0.90)},
    "SYN-027": {"S1": (0.50, 0.85), "S2": (0.78, 0.85), "S3": (0.85, 0.88), "S4": (0.90, 0.88)},
    "SYN-032": {"S1": (0.78, 0.88), "S2": (0.82, 0.88), "S4": (0.88, 0.88), "S5": (0.92, 0.90)},
    "SYN-036": {"S1": (0.70, 0.85), "S2": (0.80, 0.85), "S3": (0.85, 0.88), "S4": (0.85, 0.88), "S5": (0.92, 0.90)},
    "SYN-047": {"S1": (0.72, 0.85), "S2": (0.80, 0.85), "S3": (0.85, 0.88), "S4": (0.92, 0.90)},
    # ---- burst workers ----
    "SYN-005": {"S1": (0.55, 0.80), "S2": (0.85, 0.85)},
    "SYN-013": {"S1": (0.45, 0.75), "S2": (0.60, 0.80), "S3": (0.85, 0.85)},
    "SYN-017": {"S1": (0.60, 0.82), "S2": (0.65, 0.82), "S3": (0.72, 0.80), "S4": (0.85, 0.85)},
    "SYN-022": {"S1": (0.55, 0.80), "S2": (0.62, 0.82), "S3": (0.70, 0.80), "S4": (0.88, 0.85)},
    "SYN-033": {"S1": (0.48, 0.78), "S2": (0.60, 0.80), "S3": (0.66, 0.80), "S4": (0.80, 0.82), "S5": (0.88, 0.85)},
    "SYN-037": {"S1": (0.62, 0.85), "S2": (0.68, 0.85), "S3": (0.75, 0.85), "S4": (0.85, 0.85), "S5": (0.90, 0.85)},
    "SYN-048": {"S1": (0.58, 0.82), "S2": (0.70, 0.85), "S3": (0.68, 0.82), "S4": (0.85, 0.85)},
    # ---- reviewers and coordinators (small changes, often refactored by others) ----
    "SYN-003": {"S1": (0.35, 0.75), "S2": (0.60, 0.75)},
    "SYN-008": {"S1": (0.40, 0.80), "S2": (0.55, 0.80), "S3": (0.50, 0.80)},
    "SYN-018": {"S1": (0.30, 0.75), "S2": (0.45, 0.75)},
    "SYN-023": {"S1": (0.40, 0.75), "S2": (0.45, 0.75), "S3": (0.55, 0.75), "S4": (0.70, 0.75)},
    "SYN-028": {"S2": (0.45, 0.78), "S3": (0.55, 0.78), "S4": (0.70, 0.78)},
    "SYN-038": {"S1": (0.35, 0.75), "S2": (0.45, 0.78), "S3": (0.55, 0.78), "S4": (0.70, 0.78)},
    "SYN-042": {"S1": (0.38, 0.75), "S2": (0.50, 0.78)},
    # ---- free riders (copied, pasted or replaced code) ----
    "SYN-004": {"S2": (0.30, 0.40)},
    "SYN-009": {"S2": (0.35, 0.20)},
    "SYN-014": {"S2": (0.40, 0.25)},
    "SYN-024": {"S1": (0.30, 0.15), "S2": (0.15, 0.10), "S4": (0.60, 0.10)},  # sprint 2: pasted theme later replaced
    "SYN-034": {"S2": (0.05, 0.05)},  # the pasted chart library was removed
    "SYN-039": {"S3": (0.45, 0.30), "S5": (0.50, 0.15)},
    "SYN-043": {"S2": (0.40, 0.25), "S3": (0.50, 0.50)},
    "SYN-049": {"S1": (0.60, 0.10), "S2": (0.20, 0.15)},  # sprint 2: tutorial code replaced by a teammate
    # ---- no specific pattern ----
    "SYN-010": {"S1": (0.55, 0.85), "S2": (0.70, 0.85), "S3": (0.72, 0.80)},
    "SYN-015": {"S1": (0.50, 0.85), "S2": (0.60, 0.85), "S3": (0.75, 0.85)},
    "SYN-020": {"S1": (0.85, 0.90), "S2": (0.85, 0.90), "S3": (0.75, 0.85), "S4": (0.80, 0.85)},
    "SYN-025": {"S1": (0.60, 0.80), "S2": (0.65, 0.80), "S3": (0.72, 0.80), "S4": (0.85, 0.80)},
    "SYN-029": {"S1": (0.45, 0.75), "S2": (0.40, 0.75), "S3": (0.55, 0.75), "S4": (0.85, 0.80)},  # copied handlers later folded into a helper
    "SYN-030": {"S1": (0.70, 0.90), "S2": (0.60, 0.85)},
    "SYN-035": {"S2": (0.80, 0.90), "S3": (0.60, 0.80), "S4": (0.85, 0.85), "S5": (0.80, 0.85)},
    "SYN-040": {"S4": (0.90, 0.90), "S5": (0.92, 0.90)},
    "SYN-044": {"S1": (0.70, 1.00), "S2": (0.80, 1.00), "S3": (0.88, 0.95)},
    "SYN-045": {"S1": (0.85, 0.90), "S2": (0.90, 0.90), "S3": (0.55, 0.80)},
    "SYN-050": {"S1": (0.60, 0.85), "S2": (0.70, 0.80), "S3": (0.60, 0.80), "S4": (0.85, 0.85)},
}

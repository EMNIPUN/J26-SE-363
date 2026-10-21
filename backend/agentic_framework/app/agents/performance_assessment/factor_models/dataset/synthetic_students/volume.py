"""Volume of each simulated student's work, set per student (never per team).

The commits in teams/*.py list the core change of each piece of work, so on their own they are an order of
magnitude smaller than real commits. For each student this file gives the typical net lines per active sprint that
the student's work should reach. materialize.py scales the student's own commits to that level and adds the
neighbouring files each change really touches (from the team's import graph), so lines, files, files per task and
component breadth rise together. The scale is one number per student, so the differences between a student's
sprints that were written by hand are kept.

Targets were chosen from the real students of the same type (median net lines per active sprint):
  consistent contributor 2685 (quartiles 1635-4507)   last-minute rusher 1867 (1130-2493)
  burst worker 1466 (775-2687)                         no specific pattern 1088 (800-2288)
  reviewer / coordinator 168 (98-239)                  free rider -99 to 48
None means the student's authored sizes are kept as they are (the pasted-code cases).
"""

TARGET_NET_LOC = {
    # consistent deep contributors
    "SYN-001": 2000, "SYN-006": 2800, "SYN-011": 2400, "SYN-016": 3500, "SYN-026": 4200, "SYN-031": 2600, "SYN-041": 1900, "SYN-046": 3000,
    # last-minute rushers
    "SYN-002": 1700, "SYN-007": 1500, "SYN-012": 1300, "SYN-021": 2000, "SYN-027": 1400, "SYN-032": 1800, "SYN-036": 1600, "SYN-047": 2100,
    # burst workers
    "SYN-005": 900, "SYN-013": 1400, "SYN-017": 1700, "SYN-022": 1200, "SYN-033": 2200, "SYN-037": 1500, "SYN-048": 2400,
    # reviewers and coordinators
    "SYN-003": 250, "SYN-008": 220, "SYN-018": 300, "SYN-023": 200, "SYN-028": 450, "SYN-038": 350, "SYN-042": 500,
    # free riders (SYN-024, SYN-034 and SYN-049 keep their authored sizes: pasted or copied code)
    "SYN-004": 40, "SYN-009": 60, "SYN-014": 70, "SYN-019": 30, "SYN-024": None, "SYN-034": None, "SYN-039": 60, "SYN-043": 70, "SYN-049": None,
    # no specific pattern
    "SYN-010": 1300, "SYN-015": 700, "SYN-020": 450, "SYN-025": 600, "SYN-029": 3200, "SYN-030": 1100, "SYN-035": 900, "SYN-040": 500, "SYN-044": 800,
    "SYN-045": 400, "SYN-050": 1100,
}

LINES_PER_FILE = 38  # median net lines per file touched in a real sprint (real: 38.8)

# Heavy committers split one piece of work into several commits on the same day (real consistent and burst
# students make about 18 commits per sprint; the hand-written commits give 7 to 11). 1 = commits kept as written.
SPLIT = {
    "SYN-001": 2, "SYN-006": 2, "SYN-011": 2, "SYN-016": 2, "SYN-026": 2, "SYN-031": 2, "SYN-041": 2, "SYN-046": 2,   # consistent
    "SYN-005": 2, "SYN-013": 2, "SYN-017": 2, "SYN-022": 2, "SYN-033": 2, "SYN-037": 2, "SYN-048": 2,                 # burst
    "SYN-029": 2, "SYN-010": 2, "SYN-050": 2,                                                                           # no specific pattern
}
MAIN_SHARE = 0.55    # share of a scaled commit's lines that stay on the file(s) it was written for

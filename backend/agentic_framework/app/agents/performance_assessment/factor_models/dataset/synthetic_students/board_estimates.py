"""How the teams estimated their tasks (story points and subtask count), kept apart from how hard the tasks are.

Real teams do not estimate difficulty cleanly: easy but visible work is padded (UI polish, CRUD, documentation), and
work that is hard to see in advance is under-estimated (concurrency, offline sync, security, schemas). In the real
data subtask counts sit between 2 and 4 and agree with story points only loosely (rank correlation 0.6).

OVERRIDES holds the tasks where the team's estimate differs from the difficulty rated in complexity_ratings.py:
key -> (story points, subtasks). Every other task keeps its written story points and gets a subtask count squeezed
into the real range with SUBTASKS_SQUEEZE.
"""

SUBTASKS_SQUEEZE = {1: 1, 2: 2, 3: 3, 4: 3, 5: 4, 6: 4}

OVERRIDES = {
    # under-estimated: hard to see in advance
    "S01-S2-005-T1": (5, 3), "S02-S3-010-T1": (3, 3), "S02-S3-008-T1": (3, 3), "S03-S2-013-T1": (5, 3), "S03-S3-013-T1": (5, 3),
    "S03-S2-015-T1": (3, 2), "S04-S1-020-T1": (3, 2), "S04-S2-020-T1": (3, 2), "S04-S3-020-T1": (5, 3), "S04-S4-017-T1": (5, 3),
    "S04-S2-017-T1": (5, 3), "S05-S3-021-T1": (5, 3), "S06-S1-026-T2": (3, 2), "S06-S1-030-T1": (3, 2), "S06-S2-026-T1": (8, 4),
    "S06-S3-030-T1": (3, 2), "S07-S2-033-T1": (5, 3), "S07-S2-035-T1": (3, 2), "S07-S4-035-T1": (5, 3), "S08-S1-037-T1": (5, 3),
    "S08-S3-037-T1": (5, 3), "S09-S1-045-T1": (5, 3), "S09-S2-041-T1": (5, 3), "S09-S3-041-T2": (3, 2), "S10-S1-046-T1": (5, 3),
    "S10-S2-046-T1": (5, 3), "S10-S3-048-T1": (5, 3), "S10-S4-046-T1": (5, 3),
    # over-estimated: visible but simple
    "S01-S1-002-T1": (5, 3), "S01-S2-001-T2": (3, 2), "S02-S1-007-T1": (5, 3), "S03-S1-012-T2": (5, 3), "S03-S1-015-T2": (3, 2),
    "S03-S3-014-T2": (3, 2), "S04-S1-018-T1": (5, 3), "S04-S3-018-T1": (5, 3), "S04-S4-018-T1": (5, 3), "S04-S4-020-T1": (5, 3),
    "S05-S1-024-T1": (5, 3), "S05-S2-024-T1": (5, 3), "S05-S3-025-T1": (5, 3), "S05-S4-021-T2": (5, 3), "S05-S4-023-T1": (3, 2),
    "S06-S1-029-T1": (5, 3), "S06-S2-029-T1": (5, 3), "S06-S2-029-T2": (3, 2), "S06-S4-028-T1": (3, 2), "S06-S4-029-T1": (3, 2),
    "S06-S4-027-T2": (5, 3), "S07-S1-034-T1": (2, 2), "S07-S3-035-T1": (5, 3), "S07-S5-035-T1": (3, 2), "S08-S1-038-T1": (5, 3),
    "S08-S5-038-T1": (5, 3), "S08-S2-038-T1": (3, 2), "S08-S5-039-T1": (2, 2), "S09-S1-044-T1": (5, 3), "S09-S3-044-T1": (3, 2),
    "S09-S3-042-T1": (5, 3), "S10-S1-050-T1": (5, 3), "S10-S4-049-T1": (2, 2), "S10-S4-050-T1": (3, 2),
}

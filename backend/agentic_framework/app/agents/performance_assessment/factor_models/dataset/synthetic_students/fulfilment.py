"""Requirement Fulfilment rating on the same 1-4 scale the real board uses.

The real board never rates above 4, and its ratings follow the acceptance criteria: nothing built is 1, partial work
is 2, all criteria met is 3, and all criteria met by clearly strong work is 4. The ratings written with the tasks used
a 1-5 scale and were more generous than the criteria they sit beside (a task with a criterion missing could still
be rated 4). This applies the real scale: the share of criteria met sets the band, and the rating written with the
task (4 or more = strong work) decides between 3 and 4 for fully met tasks.
"""


def fulfilment_rating(written, met, status, by_teammate=False):
    """written: the 1-5 rating given with the task; met: list of 0/1 per criterion."""
    if not met or status == "To Do":
        return 1
    ratio = sum(met) / len(met)
    if by_teammate:  # work done by someone else: judged on what the assignee's own part shows
        return min(written, 2)
    if ratio == 0:
        return 1 if written <= 1 else 2
    if ratio < 0.75:
        return 2
    if ratio < 1:
        return 3 if written >= 3 else 2
    return 4 if written >= 4 else 3

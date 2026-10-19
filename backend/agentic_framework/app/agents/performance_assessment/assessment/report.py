"""The lecturer's report of a run, as markdown: what was assessed, the marks with their ranges, what is missing or doubtful, and what the lecturer should look at."""
from app.agents.performance_assessment.assessment.justify import TITLES

ORDER = ("effort", "consistency", "requirement_fulfillment", "collaboration", "task_complexity", "code_ownership")


def _cell(f):
    if not f:
        return "–"
    if f["status"] == "completed" and f["score"] is not None:
        return f"{f['score']:.2f}" + ("*" if f.get("provisional") else "")
    return {"not_available": "n/a", "pending": "pending", "fallback": "failed"}.get(f["status"], f["status"])


def build_report(run: dict, sprint: dict, outcomes: dict, flags: list, quality: dict) -> str:
    final = run["mode"] == "final"
    lines = [f"# Assessment report: team {run['team_ref']}, sprint {run['sprint_id']}", "",
             f"Run type: {'final' if final else 'provisional snapshot'}. Sprint {sprint.get('start', '?')} to {sprint.get('end', '?')}.", ""]
    ok = {s: o for s, o in outcomes.items() if o["status"] != "failed"}
    failed = [s for s, o in outcomes.items() if o["status"] == "failed"]
    marks = [o["mark"] for o in ok.values() if o["mark"] is not None]
    lines += ["## Marks", "", "| Student | Mark | Range | Status | " + " | ".join(TITLES[f] for f in ORDER) + " |", "|---|---|---|---|" + "---|" * len(ORDER)]
    for sid in sorted(ok):
        o = ok[sid]
        mark = "–" if o["mark"] is None else f"{o['mark']:.0f}"
        rng = "–" if not o["interval"] else f"{o['interval'][0]:.0f} to {o['interval'][1]:.0f}"
        lines.append(f"| {sid} | {mark} | {rng} | {o['status'].replace('_', ' ')} | " + " | ".join(_cell(o["factors"].get(f)) for f in ORDER) + " |")
    if marks:
        lines += ["", f"Mean mark {sum(marks) / len(marks):.0f}, lowest {min(marks):.0f}, highest {max(marks):.0f} ({len(marks)} students)."]
    lines += ["", "`*` provisional (the sprint is not over or the score is to date). `n/a` the factor could not be measured and is left out of the mark. `pending` waiting for the student's answer to the code question."]
    if failed:
        lines += ["", "## Students that could not be assessed", ""] + [f"- {s}: {outcomes[s].get('error', 'error')}" for s in failed]
    pend = [s for s, o in ok.items() if o.get("pending")]
    if pend:
        lines += ["", "## Waiting for a code question answer", "", ", ".join(sorted(pend)) + ". Their marks are provisional until the answer arrives or both answer windows pass."]
    flagged = [s for s, o in ok.items() if o.get("flags")]
    if flagged or flags:
        lines += ["", "## For the lecturer to look at", ""]
        lines += [f"- {s}: {ok[s]['flags']} flag(s); see the student's justification and the review queue" for s in sorted(flagged)]
        lines += [f"- {f['message']}" for f in flags]
    lines += ["", "## Data quality", "", f"- {quality.get('commits_in_sprint', 0)} commits in the sprint; {quality.get('bot_commits', 0)} by bots (ignored)."]
    lines.append(f"- Authors that matched no student: {len(quality.get('unmapped_authors', {}))}, {quality.get('unmapped_share_of_added_lines', 0):.0%} of the added lines." if quality.get("unmapped_authors") else "- Every author matched a student.")
    if not quality.get("github"):
        lines.append("- GitHub review data was not available: Collaboration is not part of the marks.")
    lines += ["", "## How far to trust this", "",
              "The factor models were checked on 144 student sprints rated by an assistant, not by teaching staff. Treat every mark as a prediction to check against what you know of the team. "
              "Each student's page lists, per factor, the evidence behind the score and what to be careful about."]
    return "\n".join(lines) + "\n"

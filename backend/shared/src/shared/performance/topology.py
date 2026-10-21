"""The shape of the assessment graphs as data, shared by the agent (which runs them) and the Core API (which hands it to the frontend to draw)."""

PASSIVE = ("effort", "consistency", "collaboration", "task_complexity", "requirement_fulfillment")

TEAM_NODES = [("load_run_context", "Load run context"), ("prepare_workspace", "Prepare workspace"), ("collect_scrum", "Scrum board (MCP)"), ("collect_github", "GitHub"),
              ("build_team_evidence", "Build evidence"), ("evidence_quality_gate", "Evidence quality gate"), ("dispatch_students", "Assess students"),
              ("team_cross_check", "Team cross-check"), ("team_narrative", "Team summary"), ("team_report", "Team report"), ("publish", "Publish")]
_TEAM_META = {
    "load_run_context": ("Reads the team, its repository and the students", ["run.context"], False),
    "prepare_workspace": ("Makes a read-only copy of the repository", ["workspace.mirror"], False),
    "collect_scrum": ("Reads the sprint and its tasks from the Scrum board", ["evidence.tasks", "sprint.dates"], False),
    "collect_github": ("Reads pull requests, reviews and comments", ["evidence.pull_requests"], False),
    "build_team_evidence": ("Turns commits, tasks and reviews into evidence for each student", ["evidence.per_student", "quality"], False),
    "evidence_quality_gate": ("Checks that authors can be matched to students", ["review(identity_mapping).form"], False),
    "dispatch_students": ("Assesses every student, several at a time", ["outcomes"], False),
    "team_cross_check": ("Looks for problems across the team", ["flags"], False),
    "team_narrative": ("Writes the run summary and data-quality notes", ["summary.headline", "summary.quality_notes"], True),
    "team_report": ("Writes the report for the lecturer", ["summary.report_markdown"], False),
    "publish": ("Saves the results", ["snapshots", "summary.method", "summary.llm"], False),
}
STUDENT_NODES = [
    ("student_evidence_check", "Evidence check", "Looks at the student's evidence", [], False),
    ("factor_effort", "Effort", "How much real work", ["factors.effort.*"], False),
    ("factor_consistency", "Consistency", "How steadily", ["factors.consistency.*"], False),
    ("factor_collaboration", "Collaboration", "Reviews and discussion", ["factors.collaboration.*"], False),
    ("factor_task_complexity", "Task Complexity", "How demanding the tasks", ["factors.task_complexity.*"], False),
    ("rf_subagent", "Requirement Fulfillment", "Does the code meet the tasks", ["factors.requirement_fulfillment.*"], True),
    ("anomaly_effort", "Effort check", "Looks for signs that the effort data was gamed or inflated", ["anomalies.effort"], True),
    ("anomaly_consistency", "Consistency check", "Looks for work saved in one burst or left to the deadline", ["anomalies.consistency"], True),
    ("anomaly_collaboration", "Collaboration check", "Looks for missing, self-written or empty reviews", ["anomalies.collaboration"], True),
    ("anomaly_task_complexity", "Complexity check", "Looks for story points that the code does not support", ["anomalies.task_complexity"], True),
    ("anomaly_rf", "Requirements check", "Looks for tasks closed on the board that the code does not show", ["anomalies.requirement_fulfillment"], True),
    ("join_factors", "Join", "Collects the factor results", [], False),
    ("factor_audit", "Audit and debug", "Checks the results and re-runs a failed factor", ["findings"], False),
    ("quiz_generate", "Code questions", "Writes questions about the student's own code", ["questions[]"], True),
    ("ownership_quiz", "Code Ownership", "The state and score of the questions", ["factors.code_ownership.*"], False),
    ("behavioral_pattern", "Working pattern", "The working pattern", ["pattern.persona", "pattern.modifier", "pattern.reasons"], False),
    ("fusion", "Fusion", "Combines the factors into a mark", ["mark", "interval", "contributions"], False),
    ("investigate", "Investigate", "Looks into doubts and decides what to do", ["audit.*", "flags[]"], True),
    ("justify", "Reasons", "Builds reasons for every factor", ["factors.*.reasons", "factors.*.warnings"], False),
    ("curate_evidence", "Evidence", "Collects the evidence behind each score", ["evidence[]"], False),
    ("narrate", "Write the explanation", "Writes the brief and reasons from the evidence", ["brief.text", "why.key", "why.more", "factors.explain", "hero.summary"], True),
    ("verify_text", "Check the text", "Checks every sentence against the data", ["generated.verified", "generated.fallback_fields"], False),
    ("design_reviews", "Ask for a review", "Decides how to ask the lecturer about unsettled findings", ["review.title", "review.summary", "review.form"], True),
    ("export", "Export", "Saves the result", ["assessment_result", "factor_results"], False),
]
RF_NODES = ["map_commits", "decide", "act", "record", "critique", "revise_start", "check"]


def _edges():
    team = [(a[0], b[0]) for a, b in zip(TEAM_NODES, TEAM_NODES[1:])] + [("evidence_quality_gate", "build_team_evidence")]
    par = [n for n, *_ in STUDENT_NODES[1:6]]
    checks = [n for n, *_ in STUDENT_NODES[6:11]]  # one anomaly check after each factor, before the join
    stu = [("student_evidence_check", n) for n in par] + list(zip(par, checks)) + [(n, "join_factors") for n in checks] + [(a[0], b[0]) for a, b in zip(STUDENT_NODES[11:], STUDENT_NODES[12:])]
    rf = [("map_commits", "decide"), ("decide", "act"), ("act", "decide"), ("decide", "record"), ("record", "critique"), ("critique", "revise_start"), ("revise_start", "decide"), ("critique", "check"), ("record", "check")]
    return team, stu, rf


def topology() -> dict:
    """The graph the frontend draws. Student nodes repeat for each student (a lane); the Requirement Fulfillment sub-agent nodes are shown inside the 'rf_subagent' node."""
    team, stu, rf = _edges()
    return {"schema": "graph/2", "version": 2,
            "groups": [{"id": "team", "label": "Team run"}, {"id": "student", "label": "Student (one lane per student)", "repeat": "student", "parent": "dispatch_students"},
                       {"id": "rf", "label": "Requirement Fulfillment sub-agent", "parent": "rf_subagent"}],
            "nodes": [{"id": n, "label": l, "group": "team", "path": f"team/{n}", "description": _TEAM_META[n][0], "produces": _TEAM_META[n][1], "uses_model": _TEAM_META[n][2]} for n, l in TEAM_NODES] + [{"id": n, "label": l, "group": "student", "path": f"student:*/{n}", "description": d, "produces": p, "uses_model": m} for n, l, d, p, m in STUDENT_NODES]
                     + [{"id": n, "label": n.replace("_", " "), "group": "rf", "path": f"student:*/rf_subagent/{n}"} for n in RF_NODES],
            "edges": [{"from": a, "to": b, "group": "team"} for a, b in team] + [{"from": a, "to": b, "group": "student"} for a, b in stu] + [{"from": a, "to": b, "group": "rf"} for a, b in rf]}

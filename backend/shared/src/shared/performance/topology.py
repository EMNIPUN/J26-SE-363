"""The shape of the assessment graphs as data, shared by the agent (which runs them) and the Core API (which hands it to the frontend to draw)."""

PASSIVE = ("effort", "consistency", "collaboration", "task_complexity", "requirement_fulfillment")

TEAM_NODES = [("load_run_context", "Load run context"), ("prepare_workspace", "Prepare workspace"), ("collect_scrum", "Scrum board (MCP)"), ("collect_github", "GitHub"),
              ("build_team_evidence", "Build evidence"), ("evidence_quality_gate", "Evidence quality gate"), ("dispatch_students", "Assess students"),
              ("team_cross_check", "Team cross-check"), ("team_report", "Team report"), ("publish", "Publish")]
STUDENT_NODES = [("student_evidence_check", "Evidence check"), ("factor_effort", "Effort"), ("factor_consistency", "Consistency"), ("factor_collaboration", "Collaboration"),
                 ("factor_task_complexity", "Task Complexity"), ("rf_subagent", "Requirement Fulfillment"), ("join_factors", "Join"), ("factor_audit", "Audit and debug"),
                 ("ownership_quiz", "Code Ownership quiz"), ("behavioral_pattern", "Behavioral Pattern"), ("fusion", "Fusion"), ("explain", "Explain"), ("export", "Export")]
RF_NODES = ["map_commits", "decide", "act", "record", "critique", "revise_start", "check"]


def _edges():
    team = [(a[0], b[0]) for a, b in zip(TEAM_NODES, TEAM_NODES[1:])] + [("evidence_quality_gate", "build_team_evidence")]
    par = [n for n, _ in STUDENT_NODES[1:6]]
    stu = [("student_evidence_check", n) for n in par] + [(n, "join_factors") for n in par] + [(a[0], b[0]) for a, b in zip(STUDENT_NODES[6:], STUDENT_NODES[7:])]
    rf = [("map_commits", "decide"), ("decide", "act"), ("act", "decide"), ("decide", "record"), ("record", "critique"), ("critique", "revise_start"), ("revise_start", "decide"), ("critique", "check"), ("record", "check")]
    return team, stu, rf


def topology() -> dict:
    """The graph the frontend draws. Student nodes repeat for each student (a lane); the Requirement Fulfillment sub-agent nodes are shown inside the 'rf_subagent' node."""
    team, stu, rf = _edges()
    return {"version": 1,
            "groups": [{"id": "team", "label": "Team run"}, {"id": "student", "label": "Student (one lane per student)", "repeat": "student", "parent": "dispatch_students"},
                       {"id": "rf", "label": "Requirement Fulfillment sub-agent", "parent": "rf_subagent"}],
            "nodes": [{"id": n, "label": l, "group": "team", "path": f"team/{n}"} for n, l in TEAM_NODES] + [{"id": n, "label": l, "group": "student", "path": f"student:*/{n}"} for n, l in STUDENT_NODES]
                     + [{"id": n, "label": n.replace("_", " "), "group": "rf", "path": f"student:*/rf_subagent/{n}"} for n in RF_NODES],
            "edges": [{"from": a, "to": b, "group": "team"} for a, b in team] + [{"from": a, "to": b, "group": "student"} for a, b in stu] + [{"from": a, "to": b, "group": "rf"} for a, b in rf]}

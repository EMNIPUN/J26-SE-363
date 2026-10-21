"""LangGraph workflows of the Security Assistant (langgraph, the version pinned in pyproject.toml; no other framework).

    orchestrator_graph   the Analysis Orchestrator Agent loop      plan -> execute_action -> update_state -> plan ... -> stop
    question_graph       the Question Agent loop, per finding       ask -> score -> follow_up -> score ... -> close | escalate
    governance_graph     the stateful gate before an LLM call       check_input -> raise_scrutiny -> allow | block -> escalate
    assess_graph         the whole flow                              fetch -> scan -> governance -> interpret -> ... -> report

The graphs are the control flow. The rules stay in the core they call: agent_loop.select validates every choice against the options
the component computes for the current state, budgets come from LoopConfig, and every decision is written to audit.jsonl. A node never
acts on a choice that did not pass `select`. No checkpointer, no persistence: the state of a graph lives for one run.
"""

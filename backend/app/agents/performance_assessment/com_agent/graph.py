"""LangGraph StateGraph assembly and compilation for com_agent.

Strictly aligned with:
- BOARD.md T6.1 (T6.1.1 - T6.1.11) & T6.2 (T6.2.1 - T6.2.2)
- PLAN.md Section 1 (LangGraph StateGraph Workflow)
- PLAN.md Section 2 (Execution Lifecycle)
- PLAN.md Section 8 (AssessmentState TypedDict & Pydantic models)
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Union

from app.agents.performance_assessment.com_agent.state import (
    AssessmentState,
    ActiveVerificationState,
)
from app.agents.performance_assessment.com_agent.config.settings_loader import IS_DEV_MODE

# Import all 16 node functions
from app.agents.performance_assessment.com_agent.nodes.validation_node import (
    validate_context_node,
)
from app.agents.performance_assessment.com_agent.nodes.passive_runner_node import (
    run_effort_tool,
    run_consistency_tool,
    run_req_fulfillment_tool,
    run_collaboration_tool,
    run_complexity_tool,
    join_passive_factors_node,
)
from app.agents.performance_assessment.com_agent.nodes.active_quiz_node import (
    ast_quiz_generator_node,
    await_quiz_response_node,
    evaluate_ownership_tool,
)
from app.agents.performance_assessment.com_agent.nodes.behavioral_node import (
    run_behavioral_pattern_node,
)
from app.agents.performance_assessment.com_agent.nodes.fusion_node import (
    deterministic_fusion_node,
)
from app.agents.performance_assessment.com_agent.nodes.discrepancy_node import (
    discrepancy_detection_node,
)
from app.agents.performance_assessment.com_agent.nodes.review_node import (
    lecturer_review_node,
)
from app.agents.performance_assessment.com_agent.nodes.memory_node import (
    load_cross_sprint_memory_node,
    update_cross_sprint_memory_node,
)
from app.agents.performance_assessment.com_agent.nodes.sanitizer_node import (
    pii_redaction_sanitizer_node,
    pii_restore_node,
)
from app.agents.performance_assessment.com_agent.nodes.explanation_node import (
    generate_explanation_node,
)
from app.agents.performance_assessment.com_agent.nodes.export_node import (
    export_results_node,
)

logger = logging.getLogger(__name__)

# Try native LangGraph imports, or provide a 1:1 compatible fallback runtime
try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command
    LANGGRAPH_NATIVE = True
except ImportError:
    LANGGRAPH_NATIVE = False
    START = "__start__"
    END = "__end__"

    class MemorySaver:
        def __init__(self):
            self.storage = {}

        def get(self, config):
            thread_id = config.get("configurable", {}).get("thread_id")
            return self.storage.get(thread_id)

        def put(self, config, state):
            thread_id = config.get("configurable", {}).get("thread_id")
            self.storage[thread_id] = state

    class Command:
        def __init__(self, resume: Any = None, update: Optional[Dict[str, Any]] = None):
            self.resume = resume
            self.update = update or {}

    class StateGraph:
        """Lightweight 1:1 compatible StateGraph execution engine when langgraph package is absent."""
        def __init__(self, state_schema):
            self.state_schema = state_schema
            self.nodes: Dict[str, Callable] = {}
            self.edges: List[tuple] = []
            self.conditional_edges: Dict[str, tuple] = {}

        def add_node(self, name: str, fn: Callable):
            self.nodes[name] = fn

        def add_edge(self, from_node: str, to_node: str):
            self.edges.append((from_node, to_node))

        def add_conditional_edges(self, from_node: str, router_fn: Callable, path_map: Optional[Dict] = None):
            self.conditional_edges[from_node] = (router_fn, path_map or {})

        def compile(self, checkpointer: Optional[Any] = None, store: Optional[Any] = None):
            return CompiledGraph(self, checkpointer=checkpointer, store=store)


class CompiledGraph:
    """Compiled state graph runtime supporting checkpointers and async execution."""
    def __init__(self, graph_def: StateGraph, checkpointer: Optional[Any] = None, store: Optional[Any] = None):
        self.graph_def = graph_def
        self.checkpointer = checkpointer or MemorySaver()
        self.store = store if store is not None else {}

    def _apply_update(self, current_state: Dict[str, Any], update: Dict[str, Any]) -> None:
        if not update:
            return
        for k, v in update.items():
            if k == "factor_scores" and isinstance(v, dict):
                merged = dict(current_state.get("factor_scores") or {})
                merged.update(v)
                current_state["factor_scores"] = merged
            else:
                current_state[k] = v

    async def ainvoke(self, input_data: Any, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cfg = config or {"configurable": {"thread_id": "default"}}
        thread_id = cfg.get("configurable", {}).get("thread_id", "default")

        # 1. Check if resuming from command
        if isinstance(input_data, Command) or (isinstance(input_data, dict) and "__resume__" in input_data):
            resume_val = input_data.resume if isinstance(input_data, Command) else input_data.get("__resume__")
            saved_state = self.checkpointer.get(cfg) or {}
            current_state = {**saved_state}

            # Resume routing based on current_step
            step = current_state.get("current_step")
            if step in ["quiz_generated", "quiz_extended_waiting"]:
                upd = await await_quiz_response_node(current_state, mock_resume_value=resume_val)
                self._apply_update(current_state, upd)
                if current_state.get("current_step") == "quiz_extended_waiting":
                    self.checkpointer.put(cfg, current_state)
                    return current_state
                # Proceed to evaluate ownership
                upd_eval = await evaluate_ownership_tool(current_state)
                self._apply_update(current_state, upd_eval)
            elif step == "discrepancy_checked" and current_state.get("requires_human_review"):
                upd_rev = await lecturer_review_node(current_state, mock_resume_value=resume_val)
                self._apply_update(current_state, upd_rev)
        else:
            current_state = dict(input_data)

        # 2. Main graph traversal
        # Step A: Validation
        if current_state.get("current_step") in ["initialized", None]:
            val_upd = await validate_context_node(current_state)
            self._apply_update(current_state, val_upd)
            if current_state.get("current_step") == "validation_failed":
                self.checkpointer.put(cfg, current_state)
                return current_state

        # Step B: Parallel Fan-out passive tools
        if current_state.get("current_step") == "context_validated":
            p_tasks = [
                run_effort_tool(current_state),
                run_consistency_tool(current_state),
                run_req_fulfillment_tool(current_state),
                run_collaboration_tool(current_state),
                run_complexity_tool(current_state),
            ]
            results = await asyncio.gather(*p_tasks)
            # Parallel Fan-in via operator.ior dict merge
            merged_factor_scores = dict(current_state.get("factor_scores") or {})
            for res in results:
                if "factor_scores" in res:
                    merged_factor_scores.update(res["factor_scores"])
            current_state["factor_scores"] = merged_factor_scores

            # Join passive factors
            join_upd = await join_passive_factors_node(current_state)
            self._apply_update(current_state, join_upd)

        # Step C: Quiz Generation & Interrupt
        if current_state.get("current_step") == "passive_complete":
            q_upd = await ast_quiz_generator_node(current_state)
            self._apply_update(current_state, q_upd)
            # Save checkpoint and pause for student response
            self.checkpointer.put(cfg, current_state)
            return current_state

        # Step D: Behavioral Persona -> Fusion -> Discrepancy
        if current_state.get("current_step") in ["quiz_evaluated", "ownership_evaluated"]:
            b_upd = await run_behavioral_pattern_node(current_state)
            self._apply_update(current_state, b_upd)

            f_upd = await deterministic_fusion_node(current_state)
            self._apply_update(current_state, f_upd)

            d_upd = await discrepancy_detection_node(current_state)
            self._apply_update(current_state, d_upd)

            if current_state.get("requires_human_review"):
                # Pause at lecturer review
                self.checkpointer.put(cfg, current_state)
                return current_state

        # Step E: Memory -> Redaction -> Explanation -> Restore -> Memory Update -> Export
        if current_state.get("current_step") in ["discrepancy_checked", "lecturer_review_completed"]:
            m_load_upd = await load_cross_sprint_memory_node(current_state, store=self.store)
            self._apply_update(current_state, m_load_upd)

            redact_upd = await pii_redaction_sanitizer_node(current_state)
            self._apply_update(current_state, redact_upd)

            exp_upd = await generate_explanation_node(current_state)
            self._apply_update(current_state, exp_upd)

            rest_upd = await pii_restore_node(current_state)
            self._apply_update(current_state, rest_upd)

            m_save_upd = await update_cross_sprint_memory_node(current_state, store=self.store)
            self._apply_update(current_state, m_save_upd)

            exp_final = await export_results_node(current_state)
            self._apply_update(current_state, exp_final)

            self.checkpointer.put(cfg, current_state)

        return current_state


def make_thread_config(sprint_id: str, student_id: str) -> Dict[str, Any]:
    """T6.2.1: Helper generating isolated thread configuration for LangGraph."""
    return {"configurable": {"thread_id": f"sprint_{sprint_id}_student_{student_id}"}}


def build_initial_state(student_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """T6.2.2: Build safe default initial AssessmentState dictionary."""
    ctx = student_context or {}
    return {
        "student_id": ctx.get("student_id"),
        "student_name": ctx.get("student_name"),
        "student_github_username": ctx.get("student_github_username"),
        "student_git_emails": ctx.get("student_git_emails"),
        "team_id": ctx.get("team_id"),
        "sprint_id": ctx.get("sprint_id"),
        "repo_url": ctx.get("repo_url"),
        "sprint_start": ctx.get("sprint_start"),
        "sprint_end": ctx.get("sprint_end"),
        "assigned_tasks": ctx.get("assigned_tasks"),
        "cohort_baselines": ctx.get("cohort_baselines", {}),
        "commit_history": ctx.get("commit_history", []),
        "pull_requests": ctx.get("pull_requests", []),
        "review_comments": ctx.get("review_comments", []),
        "scrum_status_history": ctx.get("scrum_status_history", []),
        "factor_scores": ctx.get("factor_scores", {}),
        "active_verification": ctx.get("active_verification") if ctx.get("active_verification") is not None else ActiveVerificationState(),
        "behavioral_persona": ctx.get("behavioral_persona"),
        "behavioral_modifier": ctx.get("behavioral_modifier", 1.00),
        "weights_used": ctx.get("weights_used", {}),
        "additive_score": ctx.get("additive_score", 0.0),
        "final_score": ctx.get("final_score", 0.0),
        "calculation_audit_trail": ctx.get("calculation_audit_trail", {}),
        "discrepancy_flags": ctx.get("discrepancy_flags", []),
        "requires_human_review": ctx.get("requires_human_review", False),
        "lecturer_reviewed": ctx.get("lecturer_reviewed", False),
        "lecturer_id": ctx.get("lecturer_id"),
        "lecturer_override_score": ctx.get("lecturer_override_score"),
        "lecturer_comments": ctx.get("lecturer_comments"),
        "review_timestamp": ctx.get("review_timestamp"),
        "historical_trajectory": ctx.get("historical_trajectory", []),
        "pii_substitution_map": ctx.get("pii_substitution_map", {}),
        "instructor_report_markdown": ctx.get("instructor_report_markdown"),
        "student_feedback_markdown": ctx.get("student_feedback_markdown"),
        "radar_chart_data": ctx.get("radar_chart_data", {}),
        "current_step": ctx.get("current_step", "initialized"),
        "errors": list(ctx.get("errors", [])),
        "ko_raw_score": ctx.get("ko_raw_score"),
        "ko_fusion_score": ctx.get("ko_fusion_score"),
        "quiz_is_extended": ctx.get("quiz_is_extended", False),
        "quiz_is_double_timed_out": ctx.get("quiz_is_double_timed_out", False),
        "quiz_extension_deadline": ctx.get("quiz_extension_deadline"),
        "github_api_call_count": ctx.get("github_api_call_count", 0),
        "github_sandbox_mode": ctx.get("github_sandbox_mode", False),
    }


def router_discrepancy_node(state: Dict[str, Any]) -> str:
    """T6.1.7: Router directing to lecturer review on CRITICAL discrepancy alerts."""
    if state.get("requires_human_review"):
        return "lecturer_review_node"
    return "load_cross_sprint_memory_node"


def build_com_agent_graph(checkpointer: Optional[Any] = None, store: Optional[Any] = None) -> Any:
    """T6.1.1 - T6.1.11: Construct and compile StateGraph with checkpointer."""
    builder = StateGraph(AssessmentState)

    # 1. Add all 16 nodes
    builder.add_node("validate_context_node", validate_context_node)
    builder.add_node("run_effort_tool", run_effort_tool)
    builder.add_node("run_consistency_tool", run_consistency_tool)
    builder.add_node("run_req_fulfillment_tool", run_req_fulfillment_tool)
    builder.add_node("run_collaboration_tool", run_collaboration_tool)
    builder.add_node("run_complexity_tool", run_complexity_tool)
    builder.add_node("join_passive_factors_node", join_passive_factors_node)
    builder.add_node("ast_quiz_generator_node", ast_quiz_generator_node)
    builder.add_node("await_quiz_response_node", await_quiz_response_node)
    builder.add_node("evaluate_ownership_tool", evaluate_ownership_tool)
    builder.add_node("run_behavioral_pattern_node", run_behavioral_pattern_node)
    builder.add_node("deterministic_fusion_node", deterministic_fusion_node)
    builder.add_node("discrepancy_detection_node", discrepancy_detection_node)
    builder.add_node("lecturer_review_node", lecturer_review_node)
    builder.add_node("load_cross_sprint_memory_node", load_cross_sprint_memory_node)
    builder.add_node("pii_redaction_sanitizer_node", pii_redaction_sanitizer_node)
    builder.add_node("generate_explanation_node", generate_explanation_node)
    builder.add_node("pii_restore_node", pii_restore_node)
    builder.add_node("update_cross_sprint_memory_node", update_cross_sprint_memory_node)
    builder.add_node("export_results_node", export_results_node)

    # 2. Add edges
    builder.add_edge(START, "validate_context_node")
    # Parallel fan-out
    builder.add_edge("validate_context_node", "run_effort_tool")
    builder.add_edge("validate_context_node", "run_consistency_tool")
    builder.add_edge("validate_context_node", "run_req_fulfillment_tool")
    builder.add_edge("validate_context_node", "run_collaboration_tool")
    builder.add_edge("validate_context_node", "run_complexity_tool")
    # Parallel fan-in
    builder.add_edge("run_effort_tool", "join_passive_factors_node")
    builder.add_edge("run_consistency_tool", "join_passive_factors_node")
    builder.add_edge("run_req_fulfillment_tool", "join_passive_factors_node")
    builder.add_edge("run_collaboration_tool", "join_passive_factors_node")
    builder.add_edge("run_complexity_tool", "join_passive_factors_node")

    # Sequential active verification
    builder.add_edge("join_passive_factors_node", "ast_quiz_generator_node")
    builder.add_edge("ast_quiz_generator_node", "await_quiz_response_node")
    builder.add_edge("await_quiz_response_node", "evaluate_ownership_tool")
    builder.add_edge("evaluate_ownership_tool", "run_behavioral_pattern_node")
    builder.add_edge("run_behavioral_pattern_node", "deterministic_fusion_node")
    builder.add_edge("deterministic_fusion_node", "discrepancy_detection_node")

    # Conditional edge
    builder.add_conditional_edges(
        "discrepancy_detection_node",
        router_discrepancy_node,
        {
            "lecturer_review_node": "lecturer_review_node",
            "load_cross_sprint_memory_node": "load_cross_sprint_memory_node",
        },
    )
    builder.add_edge("lecturer_review_node", "load_cross_sprint_memory_node")

    # Final explanation, persistence, and export pipeline
    builder.add_edge("load_cross_sprint_memory_node", "pii_redaction_sanitizer_node")
    builder.add_edge("pii_redaction_sanitizer_node", "generate_explanation_node")
    builder.add_edge("generate_explanation_node", "pii_restore_node")
    builder.add_edge("pii_restore_node", "update_cross_sprint_memory_node")
    builder.add_edge("update_cross_sprint_memory_node", "export_results_node")
    builder.add_edge("export_results_node", END)

    # Checkpointer configuration
    cp = checkpointer or MemorySaver()
    st = store if store is not None else {}
    return builder.compile(checkpointer=cp, store=st)

"""Tool-selection policy tests for the quality ReAct graph."""

from app.agents.project_planning.schemas import Smell
from app.agents.project_planning.subagents.quality.graph import (
    TOOL_CROSS_REQ_CHECKER,
    TOOL_DIMENSION_SCORER,
    TOOL_EXEMPLAR_RETRIEVER,
    TOOL_SMELL_DETECTOR,
    TOOL_STANDARD_RETRIEVER,
    reason,
)


def _state(**overrides):
    state = {
        "requirement_text": "The system shall export a report in PDF format.",
        "other_texts": [],
        "tools_run": [],
        "iterations": 0,
    }
    state.update(overrides)
    return state


def test_clean_requirement_skips_optional_retrieval_tools():
    first = reason(_state())
    assert first["pending_tool"] == TOOL_SMELL_DETECTOR

    after_smell_check = reason(_state(
        tools_run=[TOOL_SMELL_DETECTOR],
        smells=[],
        iterations=1,
    ))
    assert after_smell_check["pending_tool"] == TOOL_DIMENSION_SCORER


def test_wording_smells_trigger_standards_and_exemplar_help():
    smells = [Smell(type="vague_term", span="fast")]
    select_standards = reason(_state(
        tools_run=[TOOL_SMELL_DETECTOR], smells=smells, iterations=1,
    ))
    assert select_standards["pending_tool"] == TOOL_STANDARD_RETRIEVER

    select_exemplar = reason(_state(
        tools_run=[TOOL_SMELL_DETECTOR, TOOL_STANDARD_RETRIEVER],
        smells=smells,
        iterations=2,
    ))
    assert select_exemplar["pending_tool"] == TOOL_EXEMPLAR_RETRIEVER


def test_cross_requirement_check_runs_only_for_a_lexical_overlap_candidate():
    selected = reason(_state(
        tools_run=[TOOL_SMELL_DETECTOR],
        smells=[],
        other_texts=["The system shall export a report in CSV format."],
        iterations=1,
    ))
    assert selected["pending_tool"] == TOOL_CROSS_REQ_CHECKER

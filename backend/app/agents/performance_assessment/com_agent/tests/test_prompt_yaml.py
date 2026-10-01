"""Tests for prompts YAML validation and rendering (T4.1 & T4.2)."""

import pathlib
import pytest
from app.agents.performance_assessment.com_agent.prompts.prompt_loader import (
    load_prompt_library,
    render_prompt,
    PromptLibrary,
    PromptDefinition,
)

PROMPTS_YAML_PATH = (
    pathlib.Path(__file__).resolve().parent.parent / "prompts" / "prompts.yaml"
)


def test_load_prompt_library_valid():
    library = load_prompt_library(PROMPTS_YAML_PATH)
    assert isinstance(library, PromptLibrary)
    assert library.version == "1.0.0"

    # Both prompt IDs must be present
    assert "instructor_assessment_dossier" in library.prompts
    assert "student_formative_feedback" in library.prompts


def test_instructor_assessment_dossier_definition():
    library = load_prompt_library(PROMPTS_YAML_PATH)
    dossier = library.prompts["instructor_assessment_dossier"]

    assert dossier.prompt_id == "instructor_assessment_dossier"
    assert dossier.model_parameters.get("temperature") == 0.15
    assert dossier.model_parameters.get("max_tokens") == 1500
    assert len(dossier.strict_constraints) >= 4
    assert len(dossier.input_variables) == 10

    # Ensure all input variables have matching placeholder in user_prompt_template
    for var in dossier.input_variables:
        assert f"{{{var}}}" in dossier.user_prompt_template, f"Missing placeholder {{{var}}} in dossier"


def test_student_formative_feedback_definition():
    library = load_prompt_library(PROMPTS_YAML_PATH)
    feedback = library.prompts["student_formative_feedback"]

    assert feedback.prompt_id == "student_formative_feedback"
    assert feedback.model_parameters.get("temperature") == 0.30
    assert feedback.model_parameters.get("max_tokens") == 1000
    assert len(feedback.strict_constraints) >= 3
    assert len(feedback.input_variables) == 6

    # Ensure all input variables have matching placeholder in user_prompt_template
    for var in feedback.input_variables:
        assert f"{{{var}}}" in feedback.user_prompt_template, f"Missing placeholder {{{var}}} in feedback"


def test_render_prompt_missing_variable_raises_key_error():
    library = load_prompt_library(PROMPTS_YAML_PATH)
    feedback = library.prompts["student_formative_feedback"]

    # Provide only 3 out of 6 required variables
    partial_vars = {
        "student_name": "Alice Perera",
        "sprint_id": "sprint-02",
        "final_score": "0.85",
    }

    with pytest.raises(KeyError) as exc_info:
        render_prompt(feedback, partial_vars)

    assert "factor_scores" in str(exc_info.value)
    assert "behavioral_persona" in str(exc_info.value)


def test_render_prompt_success():
    library = load_prompt_library(PROMPTS_YAML_PATH)
    feedback = library.prompts["student_formative_feedback"]

    vars_dict = {
        "student_name": "Alice Perera",
        "sprint_id": "sprint-02",
        "final_score": "0.85",
        "factor_scores": "Effort: 0.88, Consistency: 0.75",
        "behavioral_persona": "Consistent Builder",
        "historical_trajectory": "Stable upward trend from Sprint 1",
    }

    sys_prompt, usr_prompt = render_prompt(feedback, vars_dict)

    assert isinstance(sys_prompt, str) and len(sys_prompt) > 0
    assert isinstance(usr_prompt, str) and len(usr_prompt) > 0
    assert "Alice Perera" in usr_prompt
    assert "sprint-02" in usr_prompt
    assert "Consistent Builder" in usr_prompt
    assert "Supportive and Constructive" in sys_prompt
    assert "RULES:" in sys_prompt

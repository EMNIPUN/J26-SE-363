"""LLM explanation generation node for instructor dossier and student feedback.

Strictly aligned with:
- BOARD.md T5.12 (T5.12.1)
- PLAN.md Section 6 (YAML Prompt Management)
- PLAN.md Section 9 Node 13 (generate_explanation_node)
"""

import os
import logging
from typing import Dict, Any, Optional, Callable
from app.agents.performance_assessment.com_agent.prompts.prompt_loader import (
    load_prompt_library,
    render_prompt,
)
from app.agents.performance_assessment.com_agent.config.settings_loader import IS_DEV_MODE

logger = logging.getLogger(__name__)


def _format_factor_scores(factor_scores: Dict[str, Any]) -> str:
    lines = []
    for k, v in factor_scores.items():
        score = getattr(v, "score", None) if hasattr(v, "score") else v.get("score") if isinstance(v, dict) else v
        lines.append(f"- {k}: {float(score):.2f}" if score is not None else f"- {k}: N/A")
    return "\n".join(lines) if lines else "No factor scores available."


def _format_discrepancy_flags(flags: list) -> str:
    if not flags:
        return "None detected (Normal engagement profile)."
    lines = []
    for f in flags:
        code = getattr(f, "alert_code", None) or (f.get("alert_code") if isinstance(f, dict) else str(f))
        sev = getattr(f, "severity", None) or (f.get("severity") if isinstance(f, dict) else "")
        desc = getattr(f, "description", None) or (f.get("description") if isinstance(f, dict) else "")
        lines.append(f"- [{sev}] {code}: {desc}")
    return "\n".join(lines)


def _format_evidence_summary(factor_scores: Dict[str, Any]) -> str:
    lines = []
    for k, v in factor_scores.items():
        traces = getattr(v, "evidence_traces", []) if hasattr(v, "evidence_traces") else v.get("evidence_traces", []) if isinstance(v, dict) else []
        for t in traces:
            lines.append(f"- {k}: {t}")
    return "\n".join(lines) if lines else "Standard sprint development activity."


def _format_historical_trajectory(trajectory: list) -> str:
    if not trajectory:
        return "First sprint assessment (No previous sprint history)."
    lines = []
    for h in trajectory:
        s_id = h.get("sprint_id")
        score = h.get("final_score")
        persona = h.get("behavioral_persona")
        lines.append(f"- {s_id}: Score={score}, Persona={persona}")
    return "\n".join(lines)


async def generate_explanation_node(
    state: Dict[str, Any],
    llm_callable: Optional[Callable[[str, str, Dict[str, Any]], str]] = None,
    is_dev: Optional[bool] = None,
) -> Dict[str, Any]:
    """T5.12.1: Node 13 — Guardrailed Explanation Generation.

    Loads PromptLibrary, prepares anonymized dynamic placeholders,
    and synthesizes formal Instructor Dossier and Student Feedback markdown.
    """
    if is_dev is None:
        is_dev = IS_DEV_MODE

    library = load_prompt_library()
    dossier_def = library.prompts["instructor_assessment_dossier"]
    feedback_def = library.prompts["student_formative_feedback"]

    factor_scores = state.get("factor_scores", {})
    final_score_val = state.get("final_score", 0.0)
    persona_val = state.get("behavioral_persona", "Balanced Contributor")
    modifier_val = state.get("behavioral_modifier", 1.0)
    sprint_id_val = state.get("sprint_id", "sprint-01")

    # 1. Instructor Assessment Dossier
    dossier_vars = {
        "student_name": "[STUDENT_A]",
        "student_id": "[STUDENT_ID]",
        "sprint_id": sprint_id_val,
        "factor_scores": _format_factor_scores(factor_scores),
        "final_score": f"{final_score_val:.2f}",
        "behavioral_persona": persona_val,
        "behavioral_modifier": f"{modifier_val:.2f}",
        "discrepancy_flags": _format_discrepancy_flags(state.get("discrepancy_flags", [])),
        "evidence_summary": _format_evidence_summary(factor_scores),
        "historical_trajectory": _format_historical_trajectory(state.get("historical_trajectory", [])),
    }

    dossier_sys, dossier_usr = render_prompt(dossier_def, dossier_vars)

    # 2. Student Formative Feedback
    feedback_vars = {
        "student_name": "[STUDENT_A]",
        "sprint_id": sprint_id_val,
        "final_score": f"{final_score_val:.2f}",
        "factor_scores": _format_factor_scores(factor_scores),
        "behavioral_persona": persona_val,
        "historical_trajectory": _format_historical_trajectory(state.get("historical_trajectory", [])),
    }

    feedback_sys, feedback_usr = render_prompt(feedback_def, feedback_vars)

    # 3. Execute LLM Call or deterministic dev synthesizer
    llm_traces = []
    use_real = (
        state.get("use_real_llm")
        or os.getenv("USE_REAL_LLM", "").lower() in ("1", "true")
    )

    if llm_callable is not None:
        instructor_report = llm_callable(dossier_sys, dossier_usr, dossier_def.model_parameters)
        student_feedback = llm_callable(feedback_sys, feedback_usr, feedback_def.model_parameters)
    elif use_real:
        try:
            from app.agents.performance_assessment.com_agent.llm_client import groq_client
            d_params = dossier_def.model_parameters or {}
            f_params = feedback_def.model_parameters or {}

            logger.info("Executing Real Groq LLM for Instructor Assessment Dossier...")
            d_res = groq_client.complete(
                system_prompt=dossier_sys,
                user_prompt=dossier_usr,
                temperature=d_params.get("temperature", 0.15),
                max_tokens=d_params.get("max_tokens", 1500),
            )
            instructor_report = d_res["content"]
            llm_traces.append({"prompt_id": "instructor_assessment_dossier", **d_res})

            logger.info("Executing Real Groq LLM for Student Formative Feedback...")
            f_res = groq_client.complete(
                system_prompt=feedback_sys,
                user_prompt=feedback_usr,
                temperature=f_params.get("temperature", 0.30),
                max_tokens=f_params.get("max_tokens", 1000),
            )
            student_feedback = f_res["content"]
            llm_traces.append({"prompt_id": "student_formative_feedback", **f_res})
        except Exception as e:
            logger.error(f"Groq LLM call failed: {e}. Falling back to default synthesizer.", exc_info=True)
            use_real = False

    if not use_real and llm_callable is None:
        # Realistic markdown synthesis strictly respecting guardrails and anonymization
        instructor_report = (
            f"# Instructor Assessment Dossier: [STUDENT_A] ([STUDENT_ID])\n\n"
            f"**Sprint:** {sprint_id_val} | **Final Score S:** {final_score_val:.2f} / 1.00\n"
            f"**Contributor Archetype:** {persona_val} (Modifier: {modifier_val:.2f})\n\n"
            f"### Factor Breakdown\n{dossier_vars['factor_scores']}\n\n"
            f"### Attention Required & Anomalies\n{dossier_vars['discrepancy_flags']}\n\n"
            f"### Audit Evidence Traces\n{dossier_vars['evidence_summary']}\n"
        )
        student_feedback = (
            f"# Sprint Performance Feedback for [STUDENT_A]\n\n"
            f"Hi [STUDENT_A]! Here is your feedback for **{sprint_id_val}**.\n\n"
            f"**Overall Contribution Score:** {final_score_val:.2f} / 1.00\n"
            f"**Your Engineering Archetype:** {persona_val}\n\n"
            f"### Key Strengths\n"
            f"- Demonstrated consistent progress on assigned tasks.\n"
            f"- Maintained solid repository commit practices.\n\n"
            f"### Actionable Goals for Next Sprint\n"
            f"- Engage in earlier code reviews on teammates' pull requests.\n"
            f"- Distribute commits evenly throughout the sprint timeframe.\n"
        )

    return {
        "instructor_report_markdown": instructor_report,
        "student_feedback_markdown": student_feedback,
        "llm_execution_traces": llm_traces,
        "current_step": "explanation_generated",
    }

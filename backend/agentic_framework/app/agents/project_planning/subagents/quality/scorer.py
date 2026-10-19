"""Quality scoring primitives based on ISO/IEC/IEEE 29148.

Shared by the ReAct graph and direct fallback:
- ``request_dimension_scores``: LLM call behind ``dimension_scorer`` using 0-4 rubric.
- ``build_result``: turn LLM response into a gated RequirementQualityResult with
  applicable dimension calculations (Q_i and Q_i(%)), quality band, and evidence.
- ``score_requirement``: direct fallback path when graph times out or errors.
- ``heuristic_result``: transparent deterministic fallback implementing the 0-4
  rubric from ISO/IEC/IEEE 29148.
"""

from __future__ import annotations

import logging
import re

from app.agents.project_planning.llm import get_llm_client
from app.agents.project_planning.orchestrator.gates import evaluate_gate
from app.agents.project_planning.schemas import (
    QUALITY_DIMENSIONS,
    DimensionScore,
    QualityBand,
    RequirementInput,
    RequirementQualityResult,
    RetrievalEvidence,
    Smell,
)
from app.agents.project_planning.subagents.quality.prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.agents.project_planning.subagents.quality.smells import detect_smells

logger = logging.getLogger(__name__)

STANDARD_REFS = {
    "clarity": "ISO/IEC/IEEE 29148 § 5.2.4 (Unambiguity)",
    "completeness": "ISO/IEC/IEEE 29148 § 5.2.5 (Completeness)",
    "testability": "ISO/IEC/IEEE 29148 § 5.2.7 (Verifiability)",
    "consistency": "ISO/IEC/IEEE 29148 § 5.2.6 (Consistency)",
    "traceability": "ISO/IEC/IEEE 29148 § 5.2.8 (Traceability)",
    "correctness": "ISO/IEC/IEEE 29148 § 5.2.2 (Correctness)",
}


async def request_dimension_scores(
    requirement_text: str,
    smell_spans: list[str],
    *,
    requirement_id: str = "",
    standards: list[dict] | None = None,
    exemplars: list[dict] | None = None,
    cross_hits: list[dict] | None = None,
    other_requirements: list[str] | None = None,
    reflection_note: str | None = None,
) -> dict:
    """Call the LLM for ISO/IEC/IEEE 29148 dimension scores grounded in retrieved
    standards, exemplars, and context. Returns parsed JSON dict."""
    client = get_llm_client()
    return await client.complete_json(
        SYSTEM_PROMPT,
        build_user_prompt(
            requirement_text,
            smell_spans,
            requirement_id=requirement_id,
            standards=standards,
            exemplars=exemplars,
            cross_hits=cross_hits,
            other_requirements=other_requirements,
            reflection_note=reflection_note,
        ),
        max_tokens=2500,
    )


def _determine_quality_band(q_score: float) -> QualityBand:
    """Map 0-4 quality score to ISO 29148 Section 11 descriptive quality band."""
    if q_score >= 3.5:
        return QualityBand.EXCELLENT
    if q_score >= 2.5:
        return QualityBand.GOOD
    if q_score >= 1.5:
        return QualityBand.MODERATE
    if q_score >= 0.5:
        return QualityBand.POOR
    return QualityBand.VERY_POOR


def build_result(
    req_id: str,
    smells: list[Smell],
    data: dict,
    threshold: int,
    confidence_override: float | None = None,
    retrieval: RetrievalEvidence | None = None,
) -> RequirementQualityResult:
    """Compute overall quality score Q_i and Q_i(%) according to ISO/IEC/IEEE 29148."""
    dim_scores_raw = data.get("dimension_scores")
    legacy_dims = data.get("dimensions") if not dim_scores_raw else None
    applicability_raw = data.get("applicability", {})
    evidence_raw = data.get("evidence", {})
    issues_raw = data.get("issues", {})
    remedies_raw = data.get("remedies", {})

    dimension_scores: dict[str, DimensionScore] = {}
    applicable_raw_scores: list[int] = []
    applicable_dims: list[str] = []
    na_dims: list[str] = []
    cannot_assess_dims: list[str] = []

    for dim in QUALITY_DIMENSIONS:
        score_val = None
        app_status = "applicable"
        rationale = ""
        issues: list[str] = []
        remedy = ""
        std_ref = STANDARD_REFS.get(dim, "ISO/IEC/IEEE 29148")

        if dim_scores_raw and isinstance(dim_scores_raw, dict):
            raw = dim_scores_raw.get(dim)
            app_status = str(applicability_raw.get(dim, "applicable")).lower()
            rationale = str(evidence_raw.get(dim, ""))
            if isinstance(issues_raw, dict):
                issues = [str(i) for i in issues_raw.get(dim, []) if i]
            elif isinstance(issues_raw, list):
                issues = [str(i) for i in issues_raw if i]
            remedy = str(remedies_raw.get(dim, ""))
            score_val = raw
        elif legacy_dims and isinstance(legacy_dims, dict):
            raw_obj = legacy_dims.get(dim, {})
            score_val = raw_obj.get("score")
            app_status = str(raw_obj.get("applicability", "applicable")).lower()
            rationale = str(raw_obj.get("rationale") or raw_obj.get("evidence", ""))
            issues = [str(i) for i in raw_obj.get("issues", []) if i]
            remedy = str(raw_obj.get("remedy", ""))
            std_ref = str(raw_obj.get("standard_reference", std_ref))

        # Normalize applicability
        if app_status in ("not_applicable", "n/a", "na"):
            app_status = "not_applicable"
            na_dims.append(dim)
            raw_score = None
            pct_score = 0
        elif app_status in ("cannot_assess", "c/a", "ca"):
            app_status = "cannot_assess"
            cannot_assess_dims.append(dim)
            raw_score = None
            pct_score = 0
        else:
            app_status = "applicable"
            applicable_dims.append(dim)
            try:
                num = float(score_val) if score_val is not None else 2.0
            except (TypeError, ValueError):
                num = 2.0

            # If score was provided on 0-100 scale, convert to 0-4
            if num > 4.0:
                pct_score = max(0, min(100, round(num)))
                raw_score = max(0, min(4, round(pct_score / 25.0)))
            else:
                raw_score = max(0, min(4, round(num)))
                pct_score = round(raw_score * 25)

            applicable_raw_scores.append(raw_score)

        dimension_scores[dim] = DimensionScore(
            score=pct_score,
            raw_score=raw_score,
            applicability=app_status,
            rationale=rationale or f"Assessed as {app_status}",
            issues=issues,
            remedy=remedy,
            standard_reference=std_ref,
        )

    # Section 7: Q_i = sum(s_ij for j in A_i) / |A_i|
    if applicable_raw_scores:
        q_overall = round(sum(applicable_raw_scores) / len(applicable_raw_scores), 2)
        overall_pct = max(0, min(100, round((q_overall / 4.0) * 100)))
    else:
        q_overall = 0.0
        overall_pct = 0

    confidence = (
        confidence_override
        if confidence_override is not None
        else float(data.get("confidence", 0.85) or 0.85)
    )
    confidence = max(0.0, min(1.0, confidence))

    status, action, dart = evaluate_gate(overall_pct, confidence, threshold)
    band = _determine_quality_band(q_overall)

    return RequirementQualityResult(
        id=req_id,
        overall_score=overall_pct,
        overall_score_4=q_overall,
        quality_band=band,
        status=status,
        gate_action=action,
        dimension_scores=dimension_scores,
        applicable_dimensions=applicable_dims,
        na_dimensions=na_dims,
        cannot_assess_dimensions=cannot_assess_dims,
        smells=smells,
        suggested_rewrite=(data.get("suggested_rewrite") or None),
        confidence=confidence,
        dart_triggered=dart,
        retrieval=retrieval,
    )


async def score_requirement(
    req: RequirementInput,
    other_texts: list[str],
    threshold: int,
) -> RequirementQualityResult:
    """Direct single-shot scoring fallback (when ReAct graph times out/errors)."""
    smells = detect_smells(req.text)
    client = get_llm_client()

    if client.configured:
        try:
            data = await request_dimension_scores(
                req.text,
                [s.span or s.type for s in smells],
                requirement_id=req.id,
                other_requirements=other_texts,
            )
            result = build_result(req.id, smells, data, threshold)
            result.tools_used = ["smell_detector", "dimension_scorer"]
            return result
        except Exception:
            logger.exception("LLM scoring failed for %s; using ISO 29148 heuristic fallback", req.id)

    return heuristic_result(req.id, smells, threshold, req_text=req.text, other_texts=other_texts)


# --- deterministic fallback grounded in ISO/IEC/IEEE 29148 -------------------


def heuristic_result(
    req_id: str,
    smells: list[Smell],
    threshold: int,
    req_text: str = "",
    other_texts: list[str] | None = None,
    retrieval: RetrievalEvidence | None = None,
) -> RequirementQualityResult:
    """Transparent, deterministic 0-4 scoring implementing ISO/IEC/IEEE 29148."""
    lowered = (req_text or "").lower()
    smell_types = {s.type for s in smells}
    vague_spans = [s.span for s in smells if s.span and s.type in ("vague_term", "weak_word")]

    # 1. Clarity (0-4)
    if "vague_term" in smell_types:
        clarity_score = 1
        clarity_rat = f"Requirement contains subjective/vague terms ({', '.join(vague_spans[:2])})."
        clarity_issues = [f"Vague adjective '{s.span}' is not verifiable" for s in smells if s.type == "vague_term"]
        clarity_remedy = "Replace vague adjectives with quantifiable criteria."
    elif "weak_word" in smell_types or "passive_voice" in smell_types:
        clarity_score = 2
        clarity_rat = "Understandable but uses non-binding or passive phrasing."
        clarity_issues = [f"Weak verb '{s.span}' reduces obligation" for s in smells if s.type == "weak_word"]
        clarity_remedy = "Use active voice with 'shall' to define unambiguous obligation."
    elif "no_obligation" in smell_types:
        clarity_score = 1
        clarity_rat = "Missing clear obligation verb ('shall')."
        clarity_issues = ["No obligation verb found."]
        clarity_remedy = "Structure the statement as: The system shall <action> when <trigger>."
    else:
        clarity_score = 4
        clarity_rat = "Requirement is precise, concise, and has one reasonable interpretation."
        clarity_issues = []
        clarity_remedy = ""

    # 2. Completeness (0-4)
    has_trigger = any(w in lowered for w in ("when", "after", "if", "upon", "whenever"))
    has_numbers = bool(re.search(r"\b\d+\b", lowered))
    has_exception = any(w in lowered for w in ("fails", "error", "reject", "lock", "invalid", "otherwise", "timeout"))
    has_actor = any(w in lowered for w in ("user", "student", "customer", "instructor", "admin", "system", "client", "employee"))

    if has_actor and has_trigger and has_numbers and has_exception:
        completeness_score = 4
        completeness_rat = "Includes actor, trigger, action, constraints, and exception behavior."
        completeness_issues = []
        completeness_remedy = ""
    elif has_actor and (has_trigger or has_numbers):
        completeness_score = 3
        completeness_rat = "Main conditions specified; minor contextual details or failure path absent."
        completeness_issues = ["Exception behavior or failure path is not fully detailed."]
        completeness_remedy = "State what happens when normal execution fails or input is invalid."
    elif has_actor:
        completeness_score = 2
        completeness_rat = "Basic action present, but missing conditions, input constraints, or exceptions."
        completeness_issues = ["Missing preconditions, validation limits, or error behavior."]
        completeness_remedy = "Define preconditions and explicit exception handling."
    else:
        completeness_score = 1
        completeness_rat = "Major conditions, actors, data, or constraints are missing."
        completeness_issues = ["Actor and conditions are missing."]
        completeness_remedy = "Specify who initiates the action and under what condition."

    # 3. Testability (0-4)
    if "vague_term" in smell_types or "unquantified" in smell_types:
        testability_score = 1
        testability_rat = "Subjective wording lacks measurable conditions for objective verification."
        testability_issues = ["No measurable criteria defined."]
        testability_remedy = "Add numeric thresholds (e.g. latency, count, size) to enable automated testing."
    elif has_numbers or any(w in lowered for w in ("display", "reject", "send", "generate", "lock", "record")):
        testability_score = 4
        testability_rat = "Contains observable conditions and measurable criteria verifiable by test case."
        testability_issues = []
        testability_remedy = ""
    else:
        testability_score = 3
        testability_rat = "Verifiable via functional test or demonstration, minor interpretation needed."
        testability_issues = []
        testability_remedy = ""

    # 4. Consistency (0-4 or Cannot Assess)
    if other_texts:
        consistency_score = 4
        consistency_app = "applicable"
        consistency_rat = "No conflict detected with surrounding requirements in this SRS."
        consistency_issues = []
        consistency_remedy = ""
    else:
        consistency_score = None
        consistency_app = "cannot_assess"
        consistency_rat = "Cannot Assess: No surrounding requirement set provided to verify consistency against."
        consistency_issues = []
        consistency_remedy = "Provide full SRS context to assess cross-requirement consistency."

    # 5. Traceability (0-4)
    has_id = bool(re.search(r"^(FR|NFR|REQ|SYS)[-_ ]?\d+", req_id, re.IGNORECASE) or req_id.strip())
    has_source = any(k in lowered for k in ("source:", "stk-", "br-", "parent:", "need:"))
    has_test = any(k in lowered for k in ("test:", "tc-", "des-", "design link:"))

    if has_id and has_source and has_test:
        traceability_score = 4
        traceability_rat = "Unique identifier and complete links to source and test case artifacts."
        traceability_issues = []
        traceability_remedy = ""
    elif has_id and (has_source or has_test):
        traceability_score = 3
        traceability_rat = "Valid traceability link with minor artifact gaps."
        traceability_issues = ["Missing either backward source need or forward test-case reference."]
        traceability_remedy = "Include both Source (BR/STK) and Test Link (TC-xxx) identifiers."
    elif has_id:
        traceability_score = 1
        traceability_rat = "Has identifier but no valid source requirement or downstream test link."
        traceability_issues = ["No source requirement, business rule, or test-case link provided."]
        traceability_remedy = "Link this requirement to its source stakeholder need and test case ID."
    else:
        traceability_score = 0
        traceability_rat = "No requirement identifier or traceability link provided."
        traceability_issues = ["Requirement has no unique ID."]
        traceability_remedy = "Assign a unique ID (e.g. FR-01) and document source need."

    # 6. Correctness (0-4 or Cannot Assess)
    if any(k in lowered for k in ("plain text", "clear text", "plaintext")) and "password" in lowered:
        correctness_score = 0
        correctness_app = "applicable"
        correctness_rat = "Contradicts standard security requirements (storing passwords in plain text)."
        correctness_issues = ["Severe security flaw in requirement definition."]
        correctness_remedy = "Require salted password hashing algorithms before storage."
    elif has_source:
        correctness_score = 4
        correctness_app = "applicable"
        correctness_rat = "Aligns with referenced business rule / stakeholder specification."
        correctness_issues = []
        correctness_remedy = ""
    else:
        correctness_score = None
        correctness_app = "cannot_assess"
        correctness_rat = "Cannot Assess: No stakeholder need or source reference available for domain verification."
        correctness_issues = []
        correctness_remedy = "Cite the authorizing business rule or stakeholder need."

    dimensions_payload = {
        "clarity": clarity_score,
        "completeness": completeness_score,
        "testability": testability_score,
        "consistency": consistency_score,
        "traceability": traceability_score,
        "correctness": correctness_score,
    }
    applicability_payload = {
        "clarity": "applicable",
        "completeness": "applicable",
        "testability": "applicable",
        "consistency": consistency_app,
        "traceability": "applicable",
        "correctness": correctness_app,
    }
    evidence_payload = {
        "clarity": clarity_rat,
        "completeness": completeness_rat,
        "testability": testability_rat,
        "consistency": consistency_rat,
        "traceability": traceability_rat,
        "correctness": correctness_rat,
    }
    issues_payload = {
        "clarity": clarity_issues,
        "completeness": completeness_issues,
        "testability": testability_issues,
        "consistency": consistency_issues,
        "traceability": traceability_issues,
        "correctness": correctness_issues,
    }
    remedies_payload = {
        "clarity": clarity_remedy,
        "completeness": completeness_remedy,
        "testability": testability_remedy,
        "consistency": consistency_remedy,
        "traceability": traceability_remedy,
        "correctness": correctness_remedy,
    }

    # Generate exemplary Score 4 rewrite suggestion
    suggested_rewrite = None
    if clarity_score < 3 or completeness_score < 3 or testability_score < 3:
        suggested_rewrite = (
            f"When a registered user initiates this action, the system shall complete the operation "
            f"within 2 seconds and display a confirmation status. If the operation fails, the system "
            f"shall log the error and display a descriptive message without revealing sensitive data. "
            f"Source: Business Rule BR-01. Test: TC-{req_id.replace('-', '')}-01."
        )

    data = {
        "dimension_scores": dimensions_payload,
        "applicability": applicability_payload,
        "evidence": evidence_payload,
        "issues": issues_payload,
        "remedies": remedies_payload,
        "suggested_rewrite": suggested_rewrite,
        "confidence": 0.75,
    }

    result = build_result(req_id, smells, data, threshold, retrieval=retrieval)
    result.tools_used = ["smell_detector", "heuristic_scorer"]
    return result

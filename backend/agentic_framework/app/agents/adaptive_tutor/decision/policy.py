"""Deterministic baseline Adaptive Decision policy (no LLM).

Thresholds in ``DecisionPolicyConfig`` are provisional research defaults.
Missing mastery is never treated as zero or as an incorrect answer.
"""

from __future__ import annotations

from app.agents.adaptive_tutor.schemas import (
    AdaptiveDecisionInput,
    AdaptiveDecisionResult,
    DecisionAction,
    DecisionConceptRef,
    DecisionEvidenceRef,
    DecisionPolicyConfig,
    InterventionType,
    LearnerStateEstimate,
)

ACTION_TO_INTERVENTION: dict[DecisionAction, InterventionType] = {
    DecisionAction.REVIEW_CONCEPT: InterventionType.REVIEW_CONCEPT,
    DecisionAction.PRACTICE_CONCEPT: InterventionType.GUIDED_PRACTICE,
    DecisionAction.STUDY_PREREQUISITE: InterventionType.PREREQUISITE_REVIEW,
    DecisionAction.PROCEED_TO_TASK: InterventionType.PROJECT_GUIDANCE,
}


class DecisionPolicyError(ValueError):
    """Raised when the decision input is incomplete or inconsistent."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def apply_baseline_policy(decision_input: AdaptiveDecisionInput) -> AdaptiveDecisionResult:
    """Select the next action from task concepts, learner states, and prereqs."""
    policy = decision_input.policy
    _validate_policy(policy)

    if not decision_input.task_id.strip():
        raise DecisionPolicyError("invalid_input", "task_id is required")

    concepts = list(decision_input.required_concepts)
    if not concepts:
        raise DecisionPolicyError(
            "incomplete_input",
            "required_concepts must not be empty for a task decision",
        )

    state_by_id = _index_states(decision_input.learner_states)
    prereq_by_id = _index_states(decision_input.prerequisite_states)
    # Prerequisite states fall back to the main learner-state map.
    for concept_id, state in state_by_id.items():
        prereq_by_id.setdefault(concept_id, state)

    known_required_ids = {c.concept_id for c in concepts}
    unknown_estimate_ids = sorted(set(state_by_id) - known_required_ids)
    # Extra estimates for non-required concepts are ignored (not errors).
    _ = unknown_estimate_ids

    evidence_by_concept = _evidence_by_concept(decision_input.evidence_refs)

    # Priority: missing evidence → weak prerequisite → low mastery → practice → proceed.
    for concept in concepts:
        state = state_by_id.get(concept.concept_id)
        mastery = state.resolved_mastery() if state else None

        # Missing learner state or null mastery ⇒ insufficient evidence (not zero).
        if state is None or mastery is None:
            return _decision(
                action=DecisionAction.REVIEW_CONCEPT,
                concept=concept,
                policy=policy,
                reasons=[
                    f"Insufficient evidence for required concept {concept.concept_id!r}; "
                    "missing mastery is not treated as zero.",
                    "Recommend review / evidence gathering before practice or task progress.",
                ],
                evidence_refs=evidence_by_concept.get(concept.concept_id, []),
                priority=2,
            )

        prereq_gap = _weakest_prerequisite_gap(
            concept,
            prereq_by_id,
            policy,
        )
        if prereq_gap is not None:
            prereq_concept, prereq_reason = prereq_gap
            return _decision(
                action=DecisionAction.STUDY_PREREQUISITE,
                concept=prereq_concept,
                policy=policy,
                reasons=[
                    prereq_reason,
                    (
                        f"Required concept {concept.concept_id!r} depends on "
                        f"prerequisite {prereq_concept.concept_id!r}."
                    ),
                ],
                evidence_refs=evidence_by_concept.get(prereq_concept.concept_id, []),
                priority=1,
            )

        if mastery < policy.mastery_practice_min:
            return _decision(
                action=DecisionAction.REVIEW_CONCEPT,
                concept=concept,
                policy=policy,
                reasons=[
                    (
                        f"Mastery {mastery:.3f} for {concept.concept_id!r} is below "
                        f"provisional practice floor {policy.mastery_practice_min:.2f}."
                    ),
                    "Thresholds are provisional research defaults, not validated cutoffs.",
                ],
                evidence_refs=evidence_by_concept.get(concept.concept_id, []),
                priority=2,
            )

        if mastery < policy.mastery_sufficient:
            return _decision(
                action=DecisionAction.PRACTICE_CONCEPT,
                concept=concept,
                policy=policy,
                reasons=[
                    (
                        f"Mastery {mastery:.3f} for {concept.concept_id!r} is below "
                        f"provisional sufficiency {policy.mastery_sufficient:.2f}."
                    ),
                    "Guided practice is recommended before proceeding to the task.",
                    "Thresholds are provisional research defaults, not validated cutoffs.",
                ],
                evidence_refs=evidence_by_concept.get(concept.concept_id, []),
                priority=3,
            )

    return AdaptiveDecisionResult(
        action=DecisionAction.PROCEED_TO_TASK,
        intervention_type=ACTION_TO_INTERVENTION[DecisionAction.PROCEED_TO_TASK],
        target_concept_id=None,
        target_concept_name=None,
        learning_resource_id=None,
        reasons=[
            (
                f"All required concepts meet provisional sufficiency "
                f"({policy.mastery_sufficient:.2f}) for task {decision_input.task_id!r}."
            ),
            "Thresholds are provisional research defaults, not validated cutoffs.",
        ],
        evidence_refs=list(decision_input.evidence_refs),
        policy_id=policy.policy_id,
        priority=4,
        thresholds_provisional=True,
    )


def _validate_policy(policy: DecisionPolicyConfig) -> None:
    if policy.mastery_practice_min > policy.mastery_sufficient:
        raise DecisionPolicyError(
            "invalid_policy",
            "mastery_practice_min must be <= mastery_sufficient",
        )


def _index_states(
    states: list[LearnerStateEstimate],
) -> dict[str, LearnerStateEstimate]:
    indexed: dict[str, LearnerStateEstimate] = {}
    for state in states:
        indexed[state.concept_id] = state
    return indexed


def _evidence_by_concept(
    refs: list[DecisionEvidenceRef],
) -> dict[str, list[DecisionEvidenceRef]]:
    grouped: dict[str, list[DecisionEvidenceRef]] = {}
    for ref in refs:
        if not ref.concept_id:
            continue
        grouped.setdefault(ref.concept_id, []).append(ref)
    return grouped


def _weakest_prerequisite_gap(
    concept: DecisionConceptRef,
    prereq_states: dict[str, LearnerStateEstimate],
    policy: DecisionPolicyConfig,
) -> tuple[DecisionConceptRef, str] | None:
    """Return the weakest unsupported prerequisite, if any."""
    weakest: tuple[DecisionConceptRef, str, float] | None = None
    for prereq_id in concept.prerequisite_concept_ids:
        state = prereq_states.get(prereq_id)
        mastery = state.resolved_mastery() if state else None
        prereq_ref = DecisionConceptRef(
            concept_id=prereq_id,
            concept_name=None,
            prerequisite_concept_ids=[],
            learning_resource_ids=[],
        )
        if state is None or mastery is None:
            reason = (
                f"Prerequisite {prereq_id!r} has insufficient evidence "
                "(missing mastery is not treated as zero)."
            )
            score = -1.0
            if weakest is None or score < weakest[2]:
                weakest = (prereq_ref, reason, score)
            continue
        if mastery < policy.prerequisite_sufficient:
            reason = (
                f"Prerequisite {prereq_id!r} mastery {mastery:.3f} is below "
                f"provisional prerequisite threshold {policy.prerequisite_sufficient:.2f}."
            )
            if weakest is None or mastery < weakest[2]:
                weakest = (prereq_ref, reason, mastery)
    if weakest is None:
        return None
    return weakest[0], weakest[1]


def _decision(
    *,
    action: DecisionAction,
    concept: DecisionConceptRef,
    policy: DecisionPolicyConfig,
    reasons: list[str],
    evidence_refs: list[DecisionEvidenceRef],
    priority: int,
) -> AdaptiveDecisionResult:
    resource_id = concept.learning_resource_ids[0] if concept.learning_resource_ids else None
    return AdaptiveDecisionResult(
        action=action,
        intervention_type=ACTION_TO_INTERVENTION[action],
        target_concept_id=concept.concept_id,
        target_concept_name=concept.concept_name,
        learning_resource_id=resource_id,
        reasons=reasons,
        evidence_refs=list(evidence_refs),
        policy_id=policy.policy_id,
        priority=priority,
        thresholds_provisional=True,
    )

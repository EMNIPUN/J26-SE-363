"""Adaptive Decision Engine entry points (pure, no I/O).

Consumes typed learner-state / required-knowledge / evidence references produced
by upstream Adaptive Tutor modules. Does not estimate competency or call MCP.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.agents.adaptive_tutor.decision.policy import (
    DecisionPolicyError,
    apply_baseline_policy,
)
from app.agents.adaptive_tutor.schemas import (
    AdaptiveDecisionInput,
    AdaptiveDecisionResult,
    BktCompetencyEstimate,
    CompetencyEstimate,
    DecisionConceptRef,
    DecisionEvidenceRef,
    DecisionPolicyConfig,
    EvidenceItem,
    LearnerStateEstimate,
    SelectedRequiredConcept,
    SprintTask,
)


def decide_next_action(decision_input: AdaptiveDecisionInput) -> AdaptiveDecisionResult:
    """Run the configurable baseline policy on a typed decision input."""
    return apply_baseline_policy(decision_input)


def learner_state_from_bkt(estimate: BktCompetencyEstimate) -> LearnerStateEstimate:
    """Adapt a BKT estimate to the decision learner-state interface."""
    return LearnerStateEstimate(
        concept_id=estimate.concept_id,
        mastery_probability=estimate.mastery_probability,
        estimated_competency=None,
        observation_count=estimate.observation_count,
        evidence_count=estimate.observation_count,
        model=estimate.model,
        explanation=estimate.explanation,
    )


def learner_state_from_competency(estimate: CompetencyEstimate) -> LearnerStateEstimate:
    """Adapt a generic competency estimate to the decision learner-state interface."""
    return LearnerStateEstimate(
        concept_id=estimate.concept_id,
        mastery_probability=None,
        estimated_competency=estimate.estimated_competency,
        observation_count=estimate.evidence_count,
        evidence_count=estimate.evidence_count,
        model=None,
        explanation=estimate.explanation,
    )


def concept_ref_from_selected(
    selected: SelectedRequiredConcept,
    *,
    prerequisite_concept_ids: Sequence[str] | None = None,
) -> DecisionConceptRef:
    """Build a decision concept ref from required-knowledge selection output."""
    return DecisionConceptRef(
        concept_id=selected.concept_id,
        concept_name=selected.concept_name,
        prerequisite_concept_ids=list(prerequisite_concept_ids or []),
        learning_resource_ids=list(selected.source_lesson_ids),
        selection_role=selected.selection_role,
    )


def evidence_refs_from_items(items: Sequence[EvidenceItem]) -> list[DecisionEvidenceRef]:
    """Map normalized evidence items to decision evidence references."""
    refs: list[DecisionEvidenceRef] = []
    for item in items:
        refs.append(
            DecisionEvidenceRef(
                evidence_id=item.evidence_id,
                concept_id=item.concept_id,
                source_reference=item.source_reference,
            )
        )
    return refs


def build_decision_input(
    *,
    student_id: str,
    task: SprintTask | str,
    required_concepts: Sequence[DecisionConceptRef],
    learner_states: Sequence[LearnerStateEstimate],
    evidence_refs: Sequence[DecisionEvidenceRef] | None = None,
    prerequisite_states: Sequence[LearnerStateEstimate] | None = None,
    policy: DecisionPolicyConfig | None = None,
) -> AdaptiveDecisionInput:
    """Assemble ``AdaptiveDecisionInput`` from upstream module outputs."""
    if isinstance(task, SprintTask):
        task_id = task.task_id
        task_title = task.title
    else:
        task_id = task
        task_title = None
    return AdaptiveDecisionInput(
        student_id=student_id,
        task_id=task_id,
        task_title=task_title,
        required_concepts=list(required_concepts),
        learner_states=list(learner_states),
        evidence_refs=list(evidence_refs or []),
        prerequisite_states=list(prerequisite_states or []),
        policy=policy or DecisionPolicyConfig(),
    )


__all__ = [
    "DecisionPolicyError",
    "build_decision_input",
    "concept_ref_from_selected",
    "decide_next_action",
    "evidence_refs_from_items",
    "learner_state_from_bkt",
    "learner_state_from_competency",
]

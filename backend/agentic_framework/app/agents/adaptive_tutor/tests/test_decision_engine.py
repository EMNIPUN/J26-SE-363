"""Unit tests for the Adaptive Decision Engine baseline policy (Step 7)."""

from __future__ import annotations

import pytest

from app.agents.adaptive_tutor.decision import (
    DecisionPolicyError,
    build_decision_input,
    decide_next_action,
    learner_state_from_bkt,
    learner_state_from_competency,
)
from app.agents.adaptive_tutor.schemas import (
    AdaptiveDecisionInput,
    BktCompetencyEstimate,
    BktParameters,
    CompetencyEstimate,
    DecisionAction,
    DecisionConceptRef,
    DecisionEvidenceRef,
    DecisionPolicyConfig,
    InterventionType,
    LearnerStateEstimate,
)


JWT = "concept-jwt"
AUTH = "concept-auth"
REST = "concept-rest"
UNKNOWN = "concept-unknown"


def _concept(
    concept_id: str,
    *,
    name: str | None = None,
    prereqs: list[str] | None = None,
    resources: list[str] | None = None,
) -> DecisionConceptRef:
    return DecisionConceptRef(
        concept_id=concept_id,
        concept_name=name or concept_id,
        prerequisite_concept_ids=list(prereqs or []),
        learning_resource_ids=list(resources or []),
    )


def _state(
    concept_id: str,
    mastery: float | None,
    *,
    observations: int = 0,
) -> LearnerStateEstimate:
    return LearnerStateEstimate(
        concept_id=concept_id,
        mastery_probability=mastery,
        observation_count=observations if mastery is not None else 0,
        evidence_count=observations if mastery is not None else 0,
        model="BKT",
    )


def _input(
    *,
    concepts: list[DecisionConceptRef],
    states: list[LearnerStateEstimate],
    evidence: list[DecisionEvidenceRef] | None = None,
    prereq_states: list[LearnerStateEstimate] | None = None,
    policy: DecisionPolicyConfig | None = None,
) -> AdaptiveDecisionInput:
    return AdaptiveDecisionInput(
        student_id="student-1",
        task_id="task-jwt",
        task_title="Implement JWT Authentication",
        required_concepts=concepts,
        learner_states=states,
        evidence_refs=list(evidence or []),
        prerequisite_states=list(prereq_states or []),
        policy=policy or DecisionPolicyConfig(),
    )


def test_sufficient_knowledge_proceeds_to_task():
    decision = decide_next_action(
        _input(
            concepts=[_concept(JWT, prereqs=[AUTH])],
            states=[
                _state(JWT, 0.82, observations=3),
                _state(AUTH, 0.70, observations=2),
            ],
        )
    )
    assert decision.action is DecisionAction.PROCEED_TO_TASK
    assert decision.intervention_type is InterventionType.PROJECT_GUIDANCE
    assert decision.target_concept_id is None
    assert decision.thresholds_provisional is True
    assert "provisional" in " ".join(decision.reasons).lower()


def test_low_knowledge_recommends_review_concept():
    decision = decide_next_action(
        _input(
            concepts=[_concept(JWT, resources=["lesson-jwt"])],
            states=[_state(JWT, 0.30, observations=2)],
            evidence=[
                DecisionEvidenceRef(
                    evidence_id="ev-1",
                    concept_id=JWT,
                    source_reference="submission-1",
                )
            ],
        )
    )
    assert decision.action is DecisionAction.REVIEW_CONCEPT
    assert decision.intervention_type is InterventionType.REVIEW_CONCEPT
    assert decision.target_concept_id == JWT
    assert decision.learning_resource_id == "lesson-jwt"
    assert decision.evidence_refs[0].evidence_id == "ev-1"
    assert any("practice floor" in reason for reason in decision.reasons)


def test_mid_mastery_recommends_practice_concept():
    decision = decide_next_action(
        _input(
            concepts=[_concept(JWT)],
            states=[_state(JWT, 0.55, observations=2)],
        )
    )
    assert decision.action is DecisionAction.PRACTICE_CONCEPT
    assert decision.intervention_type is InterventionType.GUIDED_PRACTICE
    assert decision.target_concept_id == JWT


def test_missing_evidence_is_not_zero_mastery():
    decision = decide_next_action(
        _input(
            concepts=[_concept(JWT)],
            states=[_state(JWT, None, observations=0)],
        )
    )
    assert decision.action is DecisionAction.REVIEW_CONCEPT
    assert decision.target_concept_id == JWT
    joined = " ".join(decision.reasons).lower()
    assert "insufficient evidence" in joined
    assert "not treated as zero" in joined
    assert decision.action is not DecisionAction.PRACTICE_CONCEPT
    assert decision.action is not DecisionAction.PROCEED_TO_TASK


def test_missing_learner_state_treated_as_insufficient_evidence():
    decision = decide_next_action(
        _input(
            concepts=[_concept(JWT)],
            states=[],
        )
    )
    assert decision.action is DecisionAction.REVIEW_CONCEPT
    assert decision.target_concept_id == JWT
    assert "insufficient evidence" in " ".join(decision.reasons).lower()


def test_unknown_concept_estimates_are_ignored():
    """Estimates for concepts not in required set must not drive the decision."""
    decision = decide_next_action(
        _input(
            concepts=[_concept(JWT)],
            states=[
                _state(JWT, 0.80, observations=2),
                _state(UNKNOWN, 0.10, observations=5),
            ],
        )
    )
    assert decision.action is DecisionAction.PROCEED_TO_TASK
    assert decision.target_concept_id is None


def test_prerequisite_gap_with_low_prereq_mastery():
    decision = decide_next_action(
        _input(
            concepts=[_concept(JWT, prereqs=[AUTH])],
            states=[
                _state(JWT, 0.80, observations=3),
                _state(AUTH, 0.40, observations=2),
            ],
        )
    )
    assert decision.action is DecisionAction.STUDY_PREREQUISITE
    assert decision.intervention_type is InterventionType.PREREQUISITE_REVIEW
    assert decision.target_concept_id == AUTH
    assert any("prerequisite" in reason.lower() for reason in decision.reasons)


def test_prerequisite_gap_with_missing_prereq_evidence():
    decision = decide_next_action(
        _input(
            concepts=[_concept(JWT, prereqs=[AUTH])],
            states=[_state(JWT, 0.85, observations=3)],
            prereq_states=[_state(AUTH, None)],
        )
    )
    assert decision.action is DecisionAction.STUDY_PREREQUISITE
    assert decision.target_concept_id == AUTH
    assert "insufficient evidence" in " ".join(decision.reasons).lower()


def test_weakest_prerequisite_is_selected_when_multiple_gaps():
    decision = decide_next_action(
        _input(
            concepts=[_concept(JWT, prereqs=[AUTH, REST])],
            states=[
                _state(JWT, 0.90, observations=2),
                _state(AUTH, 0.50, observations=2),
                _state(REST, 0.20, observations=2),
            ],
        )
    )
    assert decision.action is DecisionAction.STUDY_PREREQUISITE
    assert decision.target_concept_id == REST


def test_incomplete_input_without_required_concepts_raises():
    with pytest.raises(DecisionPolicyError) as exc:
        decide_next_action(
            AdaptiveDecisionInput(
                student_id="student-1",
                task_id="task-jwt",
                required_concepts=[],
                learner_states=[_state(JWT, 0.9)],
            )
        )
    assert exc.value.code == "incomplete_input"


def test_conflicting_thresholds_rejected_on_policy_model():
    with pytest.raises(Exception):
        DecisionPolicyConfig(mastery_sufficient=0.4, mastery_practice_min=0.6)


def test_custom_provisional_thresholds_are_honoured():
    policy = DecisionPolicyConfig(
        policy_id="custom_provisional",
        mastery_sufficient=0.90,
        mastery_practice_min=0.70,
        prerequisite_sufficient=0.80,
    )
    decision = decide_next_action(
        _input(
            concepts=[_concept(JWT)],
            states=[_state(JWT, 0.75, observations=2)],
            policy=policy,
        )
    )
    assert decision.action is DecisionAction.PRACTICE_CONCEPT
    assert decision.policy_id == "custom_provisional"


def test_bkt_and_generic_competency_adapters():
    bkt = BktCompetencyEstimate(
        student_id="student-1",
        course_id="course-1",
        concept_id=JWT,
        mastery_probability=0.58,
        observation_count=1,
        parameters=BktParameters(),
        explanation="BKT updated from 1 observation",
    )
    generic = CompetencyEstimate(
        student_id="student-1",
        concept_id=AUTH,
        estimated_competency=None,
        confidence=0.0,
        evidence_count=0,
        explanation="No evidence collected",
    )
    decision = decide_next_action(
        build_decision_input(
            student_id="student-1",
            task="task-jwt",
            required_concepts=[_concept(AUTH), _concept(JWT)],
            learner_states=[
                learner_state_from_bkt(bkt),
                learner_state_from_competency(generic),
            ],
        )
    )
    # AUTH (missing evidence) is first in required_concepts order.
    assert decision.action is DecisionAction.REVIEW_CONCEPT
    assert decision.target_concept_id == AUTH

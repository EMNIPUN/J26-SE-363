"""Competency estimation and knowledge-gap analysis per required concept."""

from app.agents.adaptive_tutor.competency.bkt import run_bkt, update_mastery
from app.agents.adaptive_tutor.competency.compare import compare_baseline_and_fitted_bkt
from app.agents.adaptive_tutor.competency.estimate import estimate_concept_mastery_bkt
from app.agents.adaptive_tutor.competency.evaluate import (
    evaluate_baseline_and_fitted_bkt_holdout,
)
from app.agents.adaptive_tutor.competency.fit import (
    fit_bkt_parameters,
    pooled_log_likelihood,
    sequence_log_likelihood,
)
from app.agents.adaptive_tutor.competency.observations import (
    build_observations_by_concept,
    resolve_bkt_observation,
)
from app.agents.adaptive_tutor.competency.params import (
    DEFAULT_BKT_PARAMETERS,
    DEFAULT_CORRECT_THRESHOLD,
)
from app.agents.adaptive_tutor.competency.pipeline import (
    CompetencyPipelineError,
    estimate_competency_for_request,
)
from app.agents.adaptive_tutor.competency.split import (
    split_observations_by_concept,
    split_sequence_chronological,
)

__all__ = [
    "CompetencyPipelineError",
    "DEFAULT_BKT_PARAMETERS",
    "DEFAULT_CORRECT_THRESHOLD",
    "build_observations_by_concept",
    "compare_baseline_and_fitted_bkt",
    "resolve_bkt_observation",
    "estimate_competency_for_request",
    "estimate_concept_mastery_bkt",
    "evaluate_baseline_and_fitted_bkt_holdout",
    "fit_bkt_parameters",
    "pooled_log_likelihood",
    "run_bkt",
    "sequence_log_likelihood",
    "split_observations_by_concept",
    "split_sequence_chronological",
    "update_mastery",
]

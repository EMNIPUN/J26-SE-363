"""Classic Bayesian Knowledge Tracing update math.

Pure functions only: no I/O, no Neo4j, no MCP, no LLM.
"""

from __future__ import annotations

from app.agents.adaptive_tutor.schemas import BktParameters


def update_mastery(p_l: float, correct: bool, params: BktParameters) -> float:
    """Apply one BKT observation and return the updated mastery probability."""
    p_l = _clamp_probability(p_l)
    p_correct = p_l * (1.0 - params.p_s) + (1.0 - p_l) * params.p_g

    if correct:
        if p_correct <= 0.0:
            posterior = 1.0
        else:
            posterior = (p_l * (1.0 - params.p_s)) / p_correct
    else:
        p_incorrect = 1.0 - p_correct
        if p_incorrect <= 0.0:
            posterior = 0.0
        else:
            posterior = (p_l * params.p_s) / p_incorrect

    posterior = _clamp_probability(posterior)
    learned = posterior + (1.0 - posterior) * params.p_t
    return _clamp_probability(learned)


def run_bkt(
    observations: list[bool],
    params: BktParameters,
) -> tuple[float, int]:
    """Run BKT over a chronological correct/incorrect sequence.

    Returns ``(final_mastery, observation_count)``. Callers that have no usable
    observations should not treat ``params.p_l0`` as measured mastery; the
    estimator returns ``None`` instead.
    """
    p_l = params.p_l0
    for correct in observations:
        p_l = update_mastery(p_l, correct, params)
    return p_l, len(observations)


def _clamp_probability(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value

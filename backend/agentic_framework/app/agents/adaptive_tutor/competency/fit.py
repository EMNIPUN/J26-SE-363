"""Estimate classic BKT parameters from observation sequences.

Uses a constrained grid search over L0/T/G/S (no SciPy dependency).
This is a research baseline fitter for option C comparisons — not a claim of
optimal EM estimates. Insufficient data returns ``fitted=False``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from app.agents.adaptive_tutor.competency.bkt import update_mastery
from app.agents.adaptive_tutor.competency.params import DEFAULT_BKT_PARAMETERS
from app.agents.adaptive_tutor.schemas import BktFitResult, BktParameters

# Provisional minimum evidence before attempting a data-fitted model.
MIN_OBSERVATIONS_FOR_FIT = 3
MIN_SEQUENCES_FOR_FIT = 1

# Coarse grids kept small for deterministic, fast unit tests.
_L0_GRID = (0.1, 0.2, 0.3, 0.4, 0.5)
_T_GRID = (0.05, 0.1, 0.15, 0.2, 0.3)
_G_GRID = (0.05, 0.1, 0.2, 0.3)
_S_GRID = (0.05, 0.1, 0.2, 0.3)


def sequence_log_likelihood(observations: Sequence[bool], params: BktParameters) -> float:
    """Log-likelihood of one chronological correct/incorrect sequence under BKT."""
    if not observations:
        return 0.0
    p_l = params.p_l0
    total = 0.0
    for correct in observations:
        p_correct = p_l * (1.0 - params.p_s) + (1.0 - p_l) * params.p_g
        p_obs = p_correct if correct else (1.0 - p_correct)
        total += math.log(max(p_obs, 1e-12))
        p_l = update_mastery(p_l, correct, params)
    return total


def pooled_log_likelihood(
    sequences: Sequence[Sequence[bool]],
    params: BktParameters,
) -> float:
    """Sum log-likelihood across independent concept (or student) sequences."""
    return sum(sequence_log_likelihood(seq, params) for seq in sequences if seq)


def fit_bkt_parameters(
    sequences: Sequence[Sequence[bool]],
    *,
    min_observations: int = MIN_OBSERVATIONS_FOR_FIT,
    min_sequences: int = MIN_SEQUENCES_FOR_FIT,
) -> BktFitResult:
    """Fit pooled BKT parameters by maximizing in-sample log-likelihood.

    Empty / short evidence returns ``fitted=False`` without inventing parameters.
    """
    usable = [list(seq) for seq in sequences if seq]
    total_obs = sum(len(seq) for seq in usable)
    sequence_count = len(usable)

    if sequence_count < min_sequences or total_obs < min_observations:
        return BktFitResult(
            fitted=False,
            parameters=None,
            total_observations=total_obs,
            sequence_count=sequence_count,
            log_likelihood=None,
            method="grid_search_pooled",
            explanation=(
                f"Insufficient evidence to fit BKT parameters "
                f"(need ≥{min_observations} observations across ≥{min_sequences} "
                f"sequence(s); found {total_obs} obs / {sequence_count} seq)."
            ),
        )

    best_params = DEFAULT_BKT_PARAMETERS
    best_ll = float("-inf")
    for p_l0 in _L0_GRID:
        for p_t in _T_GRID:
            for p_g in _G_GRID:
                for p_s in _S_GRID:
                    candidate = BktParameters(p_l0=p_l0, p_t=p_t, p_g=p_g, p_s=p_s)
                    ll = pooled_log_likelihood(usable, candidate)
                    if ll > best_ll:
                        best_ll = ll
                        best_params = candidate

    return BktFitResult(
        fitted=True,
        parameters=best_params,
        total_observations=total_obs,
        sequence_count=sequence_count,
        log_likelihood=best_ll,
        method="grid_search_pooled",
        explanation=(
            "Fitted BKT parameters by grid search maximizing pooled in-sample "
            "log-likelihood. Treat as provisional research fit, not validated EM."
        ),
    )

"""Unit tests for classic BKT update math."""

import pytest

from app.agents.adaptive_tutor.competency import (
    DEFAULT_BKT_PARAMETERS,
    run_bkt,
    update_mastery,
)


def test_correct_observation_raises_mastery():
    start = DEFAULT_BKT_PARAMETERS.p_l0
    updated = update_mastery(start, True, DEFAULT_BKT_PARAMETERS)
    assert updated > start


def test_incorrect_observation_lowers_mastery():
    start = DEFAULT_BKT_PARAMETERS.p_l0
    updated = update_mastery(start, False, DEFAULT_BKT_PARAMETERS)
    assert updated < start


def test_mock_sequence_false_true_true_is_deterministic():
    # Hand-derived with L0=0.2, T=0.1, G=0.2, S=0.1 over [False, True, True].
    mastery, count = run_bkt([False, True, True], DEFAULT_BKT_PARAMETERS)
    assert count == 3
    assert mastery == pytest.approx(0.811764, rel=1e-5)


def test_empty_sequence_returns_prior_and_zero_count():
    mastery, count = run_bkt([], DEFAULT_BKT_PARAMETERS)
    assert count == 0
    assert mastery == DEFAULT_BKT_PARAMETERS.p_l0


def test_chronology_changes_final_mastery():
    forward, _ = run_bkt([False, True, True], DEFAULT_BKT_PARAMETERS)
    reversed_order, _ = run_bkt([True, True, False], DEFAULT_BKT_PARAMETERS)
    assert forward != reversed_order

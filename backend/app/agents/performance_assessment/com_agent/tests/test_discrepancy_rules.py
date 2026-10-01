"""Tests for discrepancy rules and anomaly heuristics (T3.4 & PLAN.md Section 9 Node 9)."""

import pytest
from app.agents.performance_assessment.com_agent.state import (
    DiscrepancyAlert,
    FactorOutput,
)
from app.agents.performance_assessment.com_agent.policies.discrepancy_rules import (
    check_ghostwriter_suspicion,
    check_deadline_panic,
    check_free_rider,
    check_unrecorded_work,
    run_all_discrepancy_checks,
    REQUIRES_HUMAN_REVIEW_SEVERITIES,
)


def test_requires_human_review_severities_constant():
    assert "CRITICAL" in REQUIRES_HUMAN_REVIEW_SEVERITIES
    assert "WARNING" not in REQUIRES_HUMAN_REVIEW_SEVERITIES
    assert "INFO" not in REQUIRES_HUMAN_REVIEW_SEVERITIES


def test_check_ghostwriter_suspicion_triggers():
    # effort > 0.75 and ko_raw < 0.35 -> CRITICAL
    alert = check_ghostwriter_suspicion(effort=0.85, ko_raw=0.20)
    assert alert is not None
    assert isinstance(alert, DiscrepancyAlert)
    assert alert.alert_code == "GHOSTWRITER_SUSPICION"
    assert alert.severity == "CRITICAL"
    assert alert.severity in REQUIRES_HUMAN_REVIEW_SEVERITIES


def test_check_ghostwriter_suspicion_normal():
    # High effort and high comprehension -> No alert
    assert check_ghostwriter_suspicion(effort=0.85, ko_raw=0.80) is None
    # Low effort and low comprehension -> No ghostwriter alert
    assert check_ghostwriter_suspicion(effort=0.30, ko_raw=0.20) is None


def test_check_deadline_panic_triggers():
    # consistency < 0.30 and effort > 0.60 -> WARNING
    alert = check_deadline_panic(consistency=0.20, effort=0.75)
    assert alert is not None
    assert alert.alert_code == "DEADLINE_PANIC"
    assert alert.severity == "WARNING"


def test_check_deadline_panic_normal():
    # Good consistency with high effort -> No panic alert
    assert check_deadline_panic(consistency=0.70, effort=0.75) is None


def test_check_free_rider_triggers():
    # effort < 0.25 and collaboration < 0.25 -> WARNING
    alert = check_free_rider(effort=0.15, collaboration=0.10)
    assert alert is not None
    assert alert.alert_code == "FREE_RIDER"
    assert alert.severity == "WARNING"


def test_check_free_rider_normal():
    # Low effort but active in collaboration
    assert check_free_rider(effort=0.15, collaboration=0.60) is None


def test_check_unrecorded_work_triggers():
    # ko_raw > 0.80 and effort < 0.40 and consistency < 0.40 -> INFO
    alert = check_unrecorded_work(effort=0.25, ko_raw=0.90, consistency=0.30)
    assert alert is not None
    assert alert.alert_code == "UNRECORDED_WORK"
    assert alert.severity == "INFO"


def test_check_unrecorded_work_normal():
    # High ownership with normal effort -> No alert
    assert check_unrecorded_work(effort=0.70, ko_raw=0.90, consistency=0.70) is None


def test_run_all_discrepancy_checks_with_factor_outputs():
    factor_scores = {
        "effort": FactorOutput(score=0.88),
        "consistency": FactorOutput(score=0.18),
        "collaboration": FactorOutput(score=0.65),
        "code_ownership": FactorOutput(
            score=0.50,
            features={"ko_raw_score": 0.22, "ko_fusion_score": 0.50},
        ),
    }

    alerts = run_all_discrepancy_checks(factor_scores)
    # effort=0.88 > 0.75 and ko_raw=0.22 < 0.35 -> GHOSTWRITER_SUSPICION
    # consistency=0.18 < 0.30 and effort=0.88 > 0.60 -> DEADLINE_PANIC
    codes = {a.alert_code for a in alerts}
    assert "GHOSTWRITER_SUSPICION" in codes
    assert "DEADLINE_PANIC" in codes
    assert len(alerts) == 2

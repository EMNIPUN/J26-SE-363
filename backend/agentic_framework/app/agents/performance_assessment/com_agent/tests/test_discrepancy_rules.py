"""Tests for discrepancy rules and anomaly heuristics (T3.4 & PLAN.md Section 9 Node 9).

Coverage improvements over original:
- Parametrized boundary-value tests at exact thresholds for all 4 rules
- Explicit absence assertions in run_all_discrepancy_checks integration tests
- NEW: free_rider and clean-profile integration scenarios
"""

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


# ---------------------------------------------------------------------------
# GHOSTWRITER_SUSPICION: effort > 0.75 AND ko_raw < 0.35
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("effort,ko_raw,should_trigger", [
    (0.85, 0.20, True),   # clearly inside
    (0.90, 0.10, True),   # clearly inside
    (0.75, 0.20, False),  # effort exactly AT 0.75 → must NOT trigger (strict >)
    (0.76, 0.20, True),   # effort just above → must trigger
    (0.85, 0.35, False),  # ko_raw exactly AT 0.35 → must NOT trigger (strict <)
    (0.85, 0.34, True),   # ko_raw just below → must trigger
    (0.85, 0.80, False),  # high effort + high comprehension → normal
    (0.30, 0.20, False),  # low effort + low comprehension → not ghostwriter
])
def test_check_ghostwriter_suspicion(effort, ko_raw, should_trigger):
    alert = check_ghostwriter_suspicion(effort=effort, ko_raw=ko_raw)
    if should_trigger:
        assert alert is not None
        assert isinstance(alert, DiscrepancyAlert)
        assert alert.alert_code == "GHOSTWRITER_SUSPICION"
        assert alert.severity == "CRITICAL"
        assert alert.severity in REQUIRES_HUMAN_REVIEW_SEVERITIES
    else:
        assert alert is None


# ---------------------------------------------------------------------------
# DEADLINE_PANIC: consistency < 0.30 AND effort > 0.60
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("consistency,effort,should_trigger", [
    (0.20, 0.75, True),   # clearly inside
    (0.30, 0.75, False),  # consistency exactly AT 0.30 → must NOT trigger (strict <)
    (0.29, 0.75, True),   # consistency just below → must trigger
    (0.20, 0.60, False),  # effort exactly AT 0.60 → must NOT trigger (strict >)
    (0.20, 0.61, True),   # effort just above → must trigger
    (0.70, 0.75, False),  # good consistency → no alert
])
def test_check_deadline_panic(consistency, effort, should_trigger):
    alert = check_deadline_panic(consistency=consistency, effort=effort)
    if should_trigger:
        assert alert is not None
        assert alert.alert_code == "DEADLINE_PANIC"
        assert alert.severity == "WARNING"
    else:
        assert alert is None


# ---------------------------------------------------------------------------
# FREE_RIDER: effort < 0.25 AND collaboration < 0.25
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("effort,collaboration,should_trigger", [
    (0.15, 0.10, True),   # clearly inside
    (0.25, 0.10, False),  # effort exactly AT 0.25 → must NOT trigger (strict <)
    (0.24, 0.10, True),   # effort just below → must trigger
    (0.10, 0.25, False),  # collaboration exactly AT 0.25 → must NOT trigger
    (0.15, 0.60, False),  # low effort but active collaboration → not a free rider
])
def test_check_free_rider(effort, collaboration, should_trigger):
    alert = check_free_rider(effort=effort, collaboration=collaboration)
    if should_trigger:
        assert alert is not None
        assert alert.alert_code == "FREE_RIDER"
        assert alert.severity == "WARNING"
    else:
        assert alert is None


# ---------------------------------------------------------------------------
# UNRECORDED_WORK: ko_raw > 0.80 AND effort < 0.40 AND consistency < 0.40
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ko_raw,effort,consistency,should_trigger", [
    (0.90, 0.25, 0.30, True),   # clearly inside
    (0.80, 0.25, 0.30, False),  # ko_raw exactly AT 0.80 → must NOT trigger (strict >)
    (0.81, 0.25, 0.30, True),   # ko_raw just above → must trigger
    (0.90, 0.40, 0.30, False),  # effort exactly AT 0.40 → must NOT trigger (strict <)
    (0.90, 0.25, 0.40, False),  # consistency exactly AT 0.40 → must NOT trigger
    (0.90, 0.70, 0.70, False),  # high ownership with normal effort → no alert
])
def test_check_unrecorded_work(ko_raw, effort, consistency, should_trigger):
    alert = check_unrecorded_work(effort=effort, ko_raw=ko_raw, consistency=consistency)
    if should_trigger:
        assert alert is not None
        assert alert.alert_code == "UNRECORDED_WORK"
        assert alert.severity == "INFO"
    else:
        assert alert is None


# ---------------------------------------------------------------------------
# run_all_discrepancy_checks: integration tests
# ---------------------------------------------------------------------------

def test_run_all_discrepancy_checks_ghostwriter_and_panic():
    """High effort + low ko_raw + low consistency triggers GHOSTWRITER + DEADLINE_PANIC only."""
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
    codes = {a.alert_code for a in alerts}

    assert "GHOSTWRITER_SUSPICION" in codes   # effort=0.88>0.75, ko_raw=0.22<0.35
    assert "DEADLINE_PANIC" in codes          # consistency=0.18<0.30, effort=0.88>0.60
    assert "FREE_RIDER" not in codes          # effort=0.88 is NOT < 0.25
    assert "UNRECORDED_WORK" not in codes     # ko_raw=0.22 is NOT > 0.80
    assert len(alerts) == 2


def test_run_all_discrepancy_checks_clean_profile():
    """Normal student profile fires zero alerts."""
    factor_scores = {
        "effort": FactorOutput(score=0.70),
        "consistency": FactorOutput(score=0.65),
        "collaboration": FactorOutput(score=0.60),
        "code_ownership": FactorOutput(
            score=0.72, features={"ko_raw_score": 0.72}
        ),
    }
    alerts = run_all_discrepancy_checks(factor_scores)
    assert alerts == []


def test_run_all_discrepancy_checks_free_rider_only():
    """Very low effort and collaboration triggers FREE_RIDER; good consistency prevents panic."""
    factor_scores = {
        "effort": FactorOutput(score=0.10),
        "consistency": FactorOutput(score=0.60),  # good → no DEADLINE_PANIC
        "collaboration": FactorOutput(score=0.05),
        "code_ownership": FactorOutput(score=0.40, features={"ko_raw_score": 0.40}),
    }
    alerts = run_all_discrepancy_checks(factor_scores)
    codes = {a.alert_code for a in alerts}
    assert "FREE_RIDER" in codes
    assert "GHOSTWRITER_SUSPICION" not in codes  # effort=0.10 is NOT > 0.75
    assert "DEADLINE_PANIC" not in codes         # effort=0.10 is NOT > 0.60
    assert len(alerts) == 1

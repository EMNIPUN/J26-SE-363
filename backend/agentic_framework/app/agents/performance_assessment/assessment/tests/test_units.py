"""Fusion, audit, justification and the factor-result adapter, without a repository or a network."""
import json
from pathlib import Path

import pytest

from app.agents.performance_assessment.assessment import audit, factors, fusion, justify
from app.agents.performance_assessment.com_agent.state import FactorOutput

FM = Path(__file__).resolve().parents[2] / "factor_models"
CARDS = {n: json.loads((FM / d / "card.json").read_text(encoding="utf-8")) for n, d in {
    "effort": "01_effort", "consistency": "02_consistency", "requirement_fulfillment": "03_requirement_fulfillment", "collaboration": "04_collaboration",
    "task_complexity": "05_task_complexity", "behavioral_pattern": "06_behavioral_pattern", "code_ownership": "07_code_ownership"}.items()}


def res(name, score, status="completed", interval=None, warnings=None, features=None, **kw):
    return {"factor": name, "score": score, "status": status, "interval": interval, "warnings": warnings or [], "versions": {}, "features": features or {}, "provisional": False, "removed": {}, "tasks": None,
            "model": None, **kw}


def all_completed(**over):
    base = {"effort": 0.6, "consistency": 0.5, "requirement_fulfillment": 0.7, "collaboration": 0.4, "task_complexity": 0.5, "code_ownership": 0.6}
    base.update(over)
    return {n: res(n, s) for n, s in base.items()}


# ---- fusion --------------------------------------------------------------------------------------------------------------------------

def test_fusion_weighted_sum_matches_hand_calculation():
    out = fusion.fuse(all_completed(), None)
    expect = 0.2 * 0.6 + 0.15 * 0.5 + 0.25 * 0.7 + 0.15 * 0.4 + 0.1 * 0.5 + 0.15 * 0.6
    assert out["mark"] == pytest.approx(100 * expect, abs=0.01)
    assert out["pending"] == [] and out["modifier"] == 1.0


def test_fusion_shares_the_weight_of_a_missing_factor_and_lists_pending():
    results = all_completed()
    del results["code_ownership"]
    results["collaboration"] = res("collaboration", None, status="not_available", warnings=["nobody reviewed"])
    out = fusion.fuse(results, None)
    assert out["pending"] == ["code_ownership"]
    assert "collaboration" in out["failed_factors"]
    assert sum(out["effective_weights"].values()) == pytest.approx(1.0)
    assert "collaboration" not in out["effective_weights"]
    assert out["mark"] == pytest.approx(100 * (0.2 * 0.6 + 0.15 * 0.5 + 0.25 * 0.7 + 0.1 * 0.5) / 0.7, abs=0.01)


def test_fusion_behavioral_modifier_only_when_applied():
    bp = {"modifier": 0.8, "applied": False}
    assert fusion.fuse(all_completed(), bp)["modifier"] == 1.0
    bp["applied"] = True
    plain, adj = fusion.fuse(all_completed(), None)["mark"], fusion.fuse(all_completed(), bp)["mark"]
    assert adj == pytest.approx(0.8 * plain, abs=0.02)


def test_fusion_without_any_score_gives_no_mark():
    out = fusion.fuse({n: res(n, None, status="not_available") for n in ("effort", "consistency")}, None)
    assert out["mark"] is None and out["mark_interval"] is None


def test_fusion_band_is_the_weighted_sum_of_factor_bands():
    results = all_completed()
    results["effort"] = res("effort", 0.6, interval=[0.5, 0.7])
    out = fusion.fuse(results, None)
    lo, hi = out["mark_interval"]
    assert lo < out["mark"] < hi


# ---- audit ---------------------------------------------------------------------------------------------------------------------------

def codes(found):
    return {f["code"] for f in found}


def test_clean_results_have_no_actionable_findings():
    found = audit.findings(all_completed(), {"student_id": "S", "tasks": []})
    assert not [f for f in found if f["severity"] != "info"]


def test_failed_factor_is_critical_and_retried_by_default():
    r = all_completed()
    r["effort"] = res("effort", None, status="fallback", warnings=["boom"])
    acts = audit.decide(audit.findings(r, {}), None)
    assert acts[0]["code"] == "failed" and acts[0]["action"] == "retry"


def test_not_available_is_info_only():
    r = all_completed()
    r["collaboration"] = res("collaboration", None, status="not_available", warnings=["no reviews"])
    found = audit.findings(r, {})
    assert codes(found) == {"not_available"} and audit.decide(found, None) == []


def test_silent_student_with_visible_work_asks_for_identity_mapping():
    r = all_completed(effort=0.0)
    ev = {"student_id": "S", "tasks": [{"status": "Done", "completed_by": "S"}], "pull_requests": []}
    acts = audit.decide(audit.findings(r, ev), None)
    a = [x for x in acts if x["code"] == "silent_but_visible"][0]
    assert a["action"] == "escalate" and a["remedy"] == "identity_mapping"


def test_ghostwriter_pattern_escalates():
    r = all_completed(effort=0.9, code_ownership=0.05)
    acts = audit.decide(audit.findings(r, {}), None)
    assert any(a["code"] == "ghostwriter" and a["action"] == "escalate" for a in acts)


def test_history_jump_escalates():
    acts = audit.decide(audit.findings(all_completed(), {}, previous_mark=90.0, mark=40.0), None)
    assert any(a["code"] == "history_jump" for a in acts)
    assert not [a for a in audit.findings(all_completed(), {}, previous_mark=50.0, mark=60.0) if a["code"] == "history_jump"]


def test_reasoning_cannot_retry_without_an_allowed_remedy_and_cannot_accept_critical_without_reason():
    r = all_completed(effort=0.9, code_ownership=0.05)
    found = audit.findings(r, {})
    gid = [f for f in found if f["code"] == "ghostwriter"][0]["id"]
    out = audit.decide(found, {"decisions": {gid: {"action": "retry", "reason": "try again please"}}})
    assert out[0]["action"] == "escalate" and "not an allowed remedy" in out[0]["reason"]
    out = audit.decide(found, {"decisions": {gid: {"action": "accept", "reason": "ok"}}})
    assert out[0]["action"] == "escalate"
    out = audit.decide(found, {"decisions": {gid: {"action": "accept", "reason": "The quiz was on a helper function the student barely touched, so the low rating is expected."}}})
    assert out[0]["action"] == "accept"


class Reply:
    def __init__(self, text, ok=True):
        self.text, self.ok = text, ok


class FakeLLM:
    model = "fake"

    def __init__(self, text, ok=True):
        self.text, self.ok, self.seen = text, ok, []

    def chat(self, messages, **kw):
        self.seen.append(messages)
        return Reply(self.text, self.ok)


def test_llm_decide_filters_unknown_findings_and_actions():
    found = audit.findings(all_completed(effort=0.9, code_ownership=0.05), {})
    gid = [f for f in found if f["code"] == "ghostwriter"][0]["id"]
    reply = json.dumps({"decisions": [{"finding": gid, "action": "escalate", "reason": "check the quiz"}, {"finding": "nope", "action": "accept", "reason": "x"}, {"finding": gid, "action": "delete", "reason": "x"}],
                        "summary": "uncertain"})
    llm = FakeLLM(reply)
    out = audit.llm_decide(llm, found, CARDS, {"effort": 0.9})
    assert list(out["decisions"]) == [gid] and out["decisions"][gid]["action"] == "escalate"
    assert "allowed_remedies" in llm.seen[0][1]["content"]  # the card reached the model
    assert audit.llm_decide(FakeLLM("not json"), found, CARDS, {}) is None
    assert audit.llm_decide(FakeLLM("{}", ok=False), found, CARDS, {}) is None
    assert audit.llm_decide(None, found, CARDS, {}) is None
    assert audit.llm_decide(llm, [f for f in found if f["severity"] == "info"], CARDS, {}) is None


# ---- justification -------------------------------------------------------------------------------------------------------------------

def test_explanation_quotes_only_numbers_from_results():
    results = all_completed()
    results["effort"] = res("effort", 0.6, features={"E_CC": 7, "E_LOC_net": 320, "E_FC": 9, "E_CT": 2}, removed={"comment": 30, "blank": 12, "format_only": 0})
    results["collaboration"] = res("collaboration", None, status="not_available", warnings=["nobody reviewed"])
    fused = fusion.fuse(results, {"modifier": 0.9, "applied": True, "persona": "Free rider", "rationale": "low effort, low collaboration", "status": "completed"})
    j = justify.explain("S", results, fused, {"sprint": {"days": 14}}, CARDS, [], "final")
    assert "7 counted commits" in " ".join(j["factors"]["effort"]["reasons"])
    assert "42 comment, blank" in " ".join(j["factors"]["effort"]["reasons"])
    assert "Collaboration" in j["summary"] and "Not part of the mark" in j["summary"]
    assert j["factors"]["behavioral_pattern"]["persona"] == "Free rider"
    assert "assistant" in j["caveats"][0]
    assert j["factors"]["effort"]["how_much_to_trust"]


def test_polish_drops_text_with_invented_numbers():
    results = all_completed()
    j = justify.explain("S", results, fusion.fuse(results, None), {}, CARDS, [], "provisional")
    assert justify.polish(None, j) is None
    assert justify.polish(FakeLLM("You scored 99 points."), j) is None
    assert justify.polish(FakeLLM(""), j) is None
    assert justify.polish(FakeLLM("A short friendly text without figures."), j) == "A short friendly text without figures."


# ---- factor results ------------------------------------------------------------------------------------------------------------------

def test_as_result_separates_not_available_from_failed():
    na = FactorOutput(score=0.0, features={"failure_kind": "not_available"}, evidence_traces=[], status="fallback_applied", error_message="nobody reviewed")
    bad = FactorOutput(score=0.0, features={"failure_kind": "error"}, evidence_traces=[], status="fallback_applied", error_message="exploded")
    ok = FactorOutput(score=0.7, features={"X": 1, "_result": {"interval": [0.6, 0.8], "warnings": ["w"], "provisional": True}}, evidence_traces=[], status="completed")
    assert factors._as_result("collaboration", na)["status"] == "not_available"
    assert factors._as_result("effort", bad)["status"] == "fallback"
    r = factors._as_result("effort", ok)
    assert r["status"] == "completed" and r["score"] == 0.7 and r["interval"] == [0.6, 0.8] and r["provisional"] and r["features"] == {"X": 1}


def test_behavioral_signals_never_turn_a_missing_factor_into_zero():
    r = all_completed()
    r["collaboration"] = res("collaboration", None, status="not_available")
    r["consistency"] = res("consistency", 0.4, features={"C_bimodal": 1, "C_DC": 0.3})
    s = factors.behavioral_signals(r)
    assert s["collaboration"] is None and s["effort"] == 0.6 and s["is_bimodal"] == 1 and s["late_churn"] == 0.3
    out = factors.run_behavioral(r, provisional=True)
    assert out["applied"] is False and out["factor"] == "behavioral_pattern"
    assert factors.run_behavioral(r, provisional=False)["applied"] in (True, False)

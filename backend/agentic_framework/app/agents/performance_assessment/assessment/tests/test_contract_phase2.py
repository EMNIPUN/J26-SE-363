from app.agents.performance_assessment.assessment.justify import (
    curate_evidence,
    early_warning_notes,
    narrate,
    verify_text,
)


def test_evidence_is_stable_and_text_verification_rejects_bad_claims():
    result = {"status": "completed", "score": 0.8, "features": {"E_CC": 2, "E_LOC_net": 10, "E_FC": 1, "E_CT": 1}}
    evidence = {"sprint": {"days": 14}}
    first = curate_evidence({"effort": result}, evidence)
    assert first == curate_evidence({"effort": result}, evidence)
    facts = {"mark": 80, "summary": "Mark 80 out of 100.", "slots": []}
    assert verify_text("Mark 80 out of 100.", facts)
    assert not verify_text("The student was lazy.", facts)
    assert not verify_text("Mark 81 out of 100.", facts)


def test_narrate_falls_back_without_mutating_score():
    facts = {"mark": 80, "summary": "Mark 80 out of 100.", "slots": [{"id": "hero_summary", "max_chars": 220}]}
    result = narrate(None, facts)
    assert result["generated"]["fallback_used"]
    assert result["slots"]["hero_summary"].startswith("Mark 80")
    assert facts["mark"] == 80


def test_early_warning_notes_are_deterministic():
    notes = early_warning_notes({"effort": {"score": 0.2, "status": "completed"}}, {})
    assert notes["low"] == "Low to date: Effort."

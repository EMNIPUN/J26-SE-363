import pytest
from shared.performance.review_forms import default_review_form, design_reviews, validate_review_form


def test_default_forms_are_closed_vocabulary():
    for kind in ("audit", "mark_check", "identity_mapping", "data_question"):
        form = default_review_form(kind, {"unmapped_authors": ["bot"], "roster": ["STU-1"]})
        assert validate_review_form(form, kind)["schema"] == "review_form/1"


def test_unsafe_agent_form_falls_back():
    proposal = {"title": "<script>", "form": {"schema": "review_form/1", "blocks": [{"type": "html"}], "fields": [], "outcomes": {"submit": {"effect": "note"}}}}
    output = design_reviews("audit", proposal=proposal)
    assert output["form"]["schema"] == "review_form/1"
    assert all(block["type"] != "html" for block in output["form"]["blocks"])


def test_validator_rejects_unknown_effect_and_external_links():
    with pytest.raises(ValueError):
        validate_review_form({"schema": "review_form/1", "blocks": [{"type": "links", "items": [{"href": "https://evil.example"}]}], "fields": [], "outcomes": {"submit": {"effect": "exec"}}}, "audit")

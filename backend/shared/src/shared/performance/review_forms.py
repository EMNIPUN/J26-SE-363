"""Closed vocabulary for agent-designed lecturer review forms."""
from __future__ import annotations

import re
from copy import deepcopy

KINDS = {"audit", "mark_check", "identity_mapping", "data_question"}
LEGACY_KINDS = {"critical_flag"}
FIELD_TYPES = {"choice", "multi_choice", "text", "textarea", "number", "slider", "mark", "date", "confirm", "author_map"}
EFFECTS = {"accept", "override", "rerun", "mapping", "note"}
BLOCK_TYPES = {"facts", "snippet", "links", "note"}
ID_RE = re.compile(r"^[a-z0-9_]+$")


def default_review_form(kind: str, evidence: dict | None = None) -> dict:
    evidence = evidence or {}
    if kind == "identity_mapping":
        authors = evidence.get("unmapped_authors", [])
        if isinstance(authors, dict):
            authors = list(authors)
        roster = evidence.get("roster", [])
        return {"schema": "review_form/1", "blocks": [{"type": "facts", "title": "Unmatched authors", "items": [
            {"label": str(a), "value": "Unmapped commit author"} for a in authors[:50]
        ]}], "fields": [
            {"id": "decision", "type": "choice", "label": "Action", "presentation": "buttons", "required": True,
             "options": [{"value": "map", "label": "Map these authors"}, {"value": "continue", "label": "Continue without mapping"}]},
            {"id": "mapping", "type": "author_map", "label": "Map these authors", "required": False,
             "authors": [{"author": str(a), "commits": 0, "lines": 0} for a in authors],
             "students": [{"id": str(s), "name": str(s)} for s in roster]}
        ], "outcomes": {"map": {"effect": "mapping", "mapping_from": "mapping"}, "continue": {"effect": "mapping", "mapping_from": "mapping"}}}
    if kind == "data_question":
        return {"schema": "review_form/1", "blocks": [], "fields": [
            {"id": "decision", "type": "choice", "label": "What should happen?", "presentation": "buttons", "required": True,
             "options": [{"value": "note", "label": "Save this note"}, {"value": "rerun", "label": "Run again"}]},
            {"id": "note", "type": "textarea", "label": "Note", "required": True, "min_length": 1, "max_length": 1000}
        ], "outcomes": {"note": {"effect": "note"}, "rerun": {"effect": "rerun", "options_from": ["note"]}}}
    return {"schema": "review_form/1", "blocks": [], "fields": [
        {"id": "decision", "type": "choice", "label": "Action", "presentation": "buttons", "required": True,
         "options": [{"value": "accept", "label": "Accept the prediction"}, {"value": "override", "label": "Set my own mark"},
                     {"value": "rerun", "label": "Run again"}]},
        {"id": "mark", "type": "mark", "label": "Mark", "required": True, "show_prediction": True, "visible_if": {"field": "decision", "equals": "override"}},
        {"id": "reason", "type": "textarea", "label": "Why", "required": True, "min_length": 10, "max_length": 1000,
         "visible_if": {"field": "decision", "equals": "override"}}
    ], "outcomes": {"accept": {"effect": "accept"}, "override": {"effect": "override", "mark_from": "mark", "reason_from": "reason"},
                    "rerun": {"effect": "rerun"}}}


def validate_review_form(form: dict, kind: str) -> dict:
    """Validate and return a defensive copy; reject anything outside review_form/1."""
    validation_kind = "audit" if kind in LEGACY_KINDS else kind
    if not isinstance(form, dict) or form.get("schema") != "review_form/1":
        raise ValueError("form must use review_form/1")
    if validation_kind not in KINDS or not isinstance(form.get("blocks"), list) or len(form.get("blocks", [])) > 4 or len(form.get("fields", [])) > 8:
        raise ValueError("invalid review form limits")
    fields = form.get("fields")
    outcomes = form.get("outcomes")
    if not isinstance(fields, list) or not isinstance(outcomes, dict):
        raise ValueError("invalid form shape")
    ids = set()
    for block in form["blocks"]:
        if not isinstance(block, dict) or block.get("type") not in BLOCK_TYPES:
            raise ValueError("invalid block type")
        raw = str(block.get("text", "")) + str(block.get("title", ""))
        if "<" in raw or ">" in raw or len(raw) > 300:
            raise ValueError("unsafe block text")
        for link in block.get("items", []):
            if isinstance(link, dict) and ("href" in link and not str(link["href"]).startswith("/teams/")):
                raise ValueError("links must be internal")
    for field in fields:
        if not isinstance(field, dict) or not ID_RE.fullmatch(str(field.get("id", ""))) or field["id"] in ids:
            raise ValueError("invalid field id")
        ids.add(field["id"])
        if field.get("type") not in FIELD_TYPES or len(str(field.get("label", ""))) > 300:
            raise ValueError("invalid field")
        if field.get("type") == "author_map" and validation_kind != "identity_mapping":
            raise ValueError("author_map is only valid for identity mapping")
        if field.get("type") == "choice" and not 2 <= len(field.get("options", [])) <= 12:
            raise ValueError("choice options must contain 2 to 12 items")
        if field.get("type") in ("choice", "multi_choice"):
            for option in field.get("options", []):
                if not isinstance(option, dict) or not ID_RE.fullmatch(str(option.get("value", ""))) or "<" in str(option.get("label", "")):
                    raise ValueError("invalid option")
        if field.get("type") == "mark" and not any(v.get("effect") == "override" for v in outcomes.values() if isinstance(v, dict)):
            raise ValueError("mark requires an override outcome")
        for condition_key in ("visible_if", "required_if"):
            condition = field.get(condition_key)
            if condition and (condition.get("field") not in ids or ("equals" not in condition and "in" not in condition)):
                raise ValueError("invalid field condition")
    if "decision" not in ids and set(outcomes) != {"submit"}:
        raise ValueError("single-action forms must have submit outcome")
    for outcome in outcomes.values():
        if not isinstance(outcome, dict) or outcome.get("effect") not in EFFECTS:
            raise ValueError("invalid outcome effect")
        for key in ("mark_from", "reason_from", "mapping_from"):
            if key in outcome and outcome[key] not in ids:
                raise ValueError("outcome references an unknown field")
    return deepcopy(form)


def design_reviews(kind: str, evidence: dict | None = None, proposal: dict | None = None) -> dict:
    """Validate an agent proposal, falling back to the safe kind-specific form."""
    form_kind = "audit" if kind in LEGACY_KINDS else kind
    if proposal is None:
        return default_review_form(form_kind, evidence)
    try:
        form = validate_review_form(proposal.get("form", proposal), form_kind)
        return {"title": str(proposal.get("title", ""))[:80], "summary": str(proposal.get("summary", ""))[:240], "form": form}
    except (TypeError, ValueError):
        fallback = default_review_form(form_kind, evidence)
        return {"title": "The agent wants a person to look at this", "summary": "", "form": fallback}

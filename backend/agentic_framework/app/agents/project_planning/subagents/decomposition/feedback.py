"""Bounded, evidence-only improvement-plan synthesis."""
from __future__ import annotations
from app.agents.project_planning.llm import get_llm_client

async def synthesize_improvement_plan(evidence: dict) -> list[dict]:
    client = get_llm_client()
    if not client.configured:
        return []
    system = '''You are a student feedback synthesizer. Use only the supplied assessment evidence.
Return JSON {"actions":[{"priority":1,"area":"parent gap|story|acceptance criterion|task","target":"id","issue":"quoted evidence","action":"concrete revision needed"}]}. Prioritize the highest impact issues. Do not rewrite a user story, acceptance criterion, or task; explain the revision needed instead. Do not invent facts.'''
    raw = await client.complete_json(system, str(evidence), max_tokens=1200)
    actions = raw.get("actions", []) if isinstance(raw, dict) else []
    return [a for a in actions if isinstance(a, dict)][:10]

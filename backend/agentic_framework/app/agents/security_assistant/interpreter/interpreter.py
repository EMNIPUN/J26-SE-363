"""LLM Semantic Interpreter: judges one scanner finding with a limited, labelled evidence bundle.

    interpreter = SemanticInterpreter(get_default_client())            # or any LLMClient, e.g. a mock
    result = await interpreter.interpret(finding, build_bundle(finding, repo_path))

It never creates findings: it needs a scanner Finding as input and its result only refers to that finding.
Built-in safety: secrets are redacted before the call; output that fails the schema is rejected; a cited
evidence id that is not in the bundle downgrades the result to "uncertain"; repository text is declared
untrusted in the prompt.
"""

import json
import re

from pydantic import ValidationError

from app.agents.security_assistant.interpreter.hooks import governance_hook
from app.agents.security_assistant.interpreter.llm import LLMClient, LLMError
from app.agents.security_assistant.interpreter.models import (
    EvidenceBundle, InterpretationResult, Verdict, finding_key,
)
from app.agents.security_assistant.interpreter.prompts import PROMPT_VERSION, build_prompt
from app.agents.security_assistant.interpreter.redaction import redact_text
from app.agents.security_assistant.schemas import Finding


class InvalidLLMOutput(ValueError):
    """The model output is not valid JSON or does not match the Verdict schema."""


def parse_verdict(text: str) -> Verdict:
    """Parse and validate model output. Raises InvalidLLMOutput; nothing is repaired or guessed."""
    cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text or "", flags=re.I)
    try:
        return Verdict.model_validate(json.loads(cleaned))
    except (ValueError, ValidationError) as exc:  # json errors are ValueError subclasses
        raise InvalidLLMOutput(str(exc)[:300]) from exc


class SemanticInterpreter:
    def __init__(self, client: LLMClient):
        self._client = client

    async def interpret(self, finding: Finding, bundle: EvidenceBundle) -> InterpretationResult:
        if not isinstance(finding, Finding) or not finding.rule_id:
            raise ValueError("the interpreter judges an existing scanner finding; it cannot create findings")
        base = dict(finding_key=finding_key(finding), category=finding.category, rule_id=finding.rule_id,
                    model=getattr(self._client, "model", None), prompt_version=PROMPT_VERSION)

        system, user = build_prompt(finding, bundle)  # redacts again
        governance_hook("pre_llm", {"finding_key": base["finding_key"], "system": system, "user": user})

        try:
            raw = await self._client.complete(system, user)
        except LLMError as exc:
            return InterpretationResult(**base, status="uncertain", error=str(exc)[:300],
                                        rationale="The LLM could not be called, so this finding was not interpreted.")
        try:
            verdict = parse_verdict(raw)
        except InvalidLLMOutput as exc:
            return InterpretationResult(**base, status="uncertain", output_rejected=True,
                                        rationale=f"LLM output rejected: {exc}")

        result = InterpretationResult(**base, status=verdict.status, rationale=redact_text(verdict.rationale),
                                      evidence_ids=verdict.evidence_ids, confidence=verdict.confidence)
        reason = self._downgrade_reason(verdict, bundle)
        if reason and verdict.status != "uncertain":
            result.original_status, result.status = verdict.status, "uncertain"
            result.downgraded, result.downgrade_reason = True, reason
        governance_hook("post_llm", {"finding_key": base["finding_key"], "result": result})
        return result

    @staticmethod
    def _downgrade_reason(verdict: Verdict, bundle: EvidenceBundle) -> str | None:
        unknown = [i for i in verdict.evidence_ids if i not in bundle.ids]
        if unknown:
            return f"cited evidence ids that are not in the bundle: {', '.join(unknown)}"
        if verdict.status != "uncertain" and not verdict.evidence_ids:
            return "a confirmed or dismissed verdict must cite at least one evidence id"
        return None

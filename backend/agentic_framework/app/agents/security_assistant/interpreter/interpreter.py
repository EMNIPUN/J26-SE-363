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

from app.agents.security_assistant import guidance as guide
from app.agents.security_assistant.interpreter.hooks import governance_hook
from app.agents.security_assistant.interpreter.llm import LLMClient, LLMError
from app.agents.security_assistant.interpreter.models import (
    CallRecord, EvidenceBundle, InterpretationResult, Verdict, finding_key,
)
from app.agents.security_assistant.interpreter.prompts import PROMPT_VERSION, build_prompt
from app.agents.security_assistant.interpreter.redaction import redact_text
from app.agents.security_assistant.pii import PIIRedactor
from app.agents.security_assistant.schemas import Finding


class InvalidLLMOutput(ValueError):
    """The model output is not valid JSON or does not match the Verdict schema."""


def parse_verdict(text: str) -> Verdict:
    """Parse and validate model output. Raises InvalidLLMOutput; nothing is repaired or guessed."""
    cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text or "", flags=re.I)
    try:
        return Verdict.model_validate(json.loads(cleaned))
    except ValidationError as exc:
        # name the fields and error types only: the message must not echo the model text into reports
        raise InvalidLLMOutput("schema errors: " + ", ".join(
            f"{'.'.join(str(p) for p in e['loc']) or 'output'} ({e['type']})" for e in exc.errors()[:6])) from exc
    except ValueError as exc:
        raise InvalidLLMOutput("output is not valid JSON") from exc


def _diagnostics(call: CallRecord | None) -> str:
    """Why an answer may have been unusable, from the call record only (never from the model's text)."""
    if call is None or call.finish_reason is None and call.output_chars is None:
        return ""
    parts = [f"finish_reason={call.finish_reason}", f"{call.output_chars} characters"]
    if call.completion_tokens is not None:
        parts.append(f"{call.completion_tokens} completion tokens")
    note = "; the output limit cut the answer off" if call.finish_reason == "length" else ""
    return f" [{', '.join(parts)}{note}]"


# a version number such as 2.0.0 or v4.17, a 40 character commit SHA, or a URL
_CONCRETE = re.compile(r"(?<![\w.])v?\d+\.\d+(?:\.\d+)*(?![\w])|(?<![0-9a-fA-F])[0-9a-f]{40}(?![0-9a-fA-F])|https?://[^\s)>\"']+")


def _ungrounded(recommendation: str, grounded: str) -> str | None:
    """The first version number, commit SHA or URL in the advice that appears nowhere in the evidence, the finding or the
    team's guidance, else None. Models invent these (a made-up "fixed in 2.0.0"); advice with one is not shown."""
    for match in _CONCRETE.finditer(recommendation):
        token = match.group(0).rstrip(".")
        if token not in grounded and token.lstrip("v") not in grounded:
            return token
    return None


class SemanticInterpreter:
    def __init__(self, client: LLMClient, pii: PIIRedactor | None = None):
        self._client = client
        self.pii = pii if pii is not None else PIIRedactor.from_env()  # its mapping stays local, never in a prompt

    async def interpret(self, finding: Finding, bundle: EvidenceBundle) -> InterpretationResult:
        if not isinstance(finding, Finding) or not finding.rule_id:
            raise ValueError("the interpreter judges an existing scanner finding; it cannot create findings")
        base = dict(finding_key=finding_key(finding), category=finding.category, rule_id=finding.rule_id,
                    model=getattr(self._client, "model", None), prompt_version=PROMPT_VERSION)

        system, user = build_prompt(finding, bundle, self.pii)  # redacts again
        governance_hook("pre_llm", {"finding_key": base["finding_key"], "system": system, "user": user})

        try:
            raw = await self._client.complete(system, user)
        except LLMError as exc:
            base["call"] = getattr(self._client, "last_call", None)
            return InterpretationResult(**base, status="uncertain", error=str(exc)[:300],
                                        rationale="The LLM could not be called, so this finding was not interpreted.")
        base["call"] = call = getattr(self._client, "last_call", None)  # finish reason, sizes, tokens: never the text
        try:
            verdict = parse_verdict(raw)
        except InvalidLLMOutput as exc:
            return InterpretationResult(**base, status="uncertain", output_rejected=True,
                                        rationale=f"LLM output rejected: {exc}{_diagnostics(call)}")

        result = InterpretationResult(**base, status=verdict.status, rationale=redact_text(verdict.rationale),
                                      evidence_ids=verdict.evidence_ids, confidence=verdict.confidence)
        reason = self._downgrade_reason(verdict, bundle)
        if reason and verdict.status != "uncertain":
            result.original_status, result.status = verdict.status, "uncertain"
            result.downgraded, result.downgrade_reason = True, reason
        if result.status == "confirmed":  # advice only for findings that were confirmed with valid evidence
            advice = redact_text(verdict.recommendation).strip()
            grounded = "\n".join([*(i.content for i in bundle.items), guide.prompt_text(guide.guidance_for(finding), finding)])
            invented = _ungrounded(advice, grounded) if advice else None
            if invented:  # a version, SHA or URL the model made up: do not show the note
                result.recommendation_dropped = f"the note named {invented!r}, which is not in the evidence or the guidance"
            else:
                result.recommendation = advice
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

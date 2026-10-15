"""Prompts for the five-step DART protocol.

Each step has a system prompt and a builder that fills in context. The LLM
returns strict JSON for every step so the graph can parse deterministically.
"""

from __future__ import annotations

import json

# ---------------------------------------------------------------------------
# Step 1 — GATHER: extract structured reasoning traces from source result
# ---------------------------------------------------------------------------

GATHER_SYSTEM = """\
You are the GATHER step of the DART (Diagnostic Arbitration using Reasoning \
Traces) protocol. You receive the raw output of a requirements-engineering \
agent (quality analysis or decomposition analysis) and extract structured \
reasoning traces — the agent's diagnosis, the evidence it relied on, the \
criteria it applied, and where it was uncertain.

Your job is NOT to re-evaluate the requirement. You are extracting what the \
source agent already concluded, organized by analytical perspective.

Reply with a STRICT JSON object only (no markdown):
{
  "traces": [
    {
      "agent_name": str,
      "diagnosis": str,
      "evidence": [str, ...],
      "criteria_used": [str, ...],
      "confidence": float,
      "recommended_action": str,
      "uncertainty_type": str
    }
  ]
}"""


def build_gather_prompt(
    requirement_text: str,
    source_stage: str,
    source_result: dict,
) -> str:
    result_json = json.dumps(source_result, indent=2, default=str)[:4000]
    return f"""Requirement under analysis:
\"\"\"{requirement_text}\"\"\"

Source agent: {source_stage}
Source agent's full output:
{result_json}

Extract every distinct analytical perspective the agent used (e.g. for quality: \
each dimension scorer, smell detector, cross-requirement checker; for \
decomposition: coverage analyzer, INVEST validator, pattern retriever). Each \
perspective becomes one reasoning trace.

Return the JSON object exactly as specified."""


# ---------------------------------------------------------------------------
# Step 2 — CATEGORIZE: classify the root cause of uncertainty
# ---------------------------------------------------------------------------

CATEGORIZE_SYSTEM = """\
You are the CATEGORIZE step of the DART protocol. Given the reasoning traces \
from Step 1, classify the ROOT CAUSE of the agent's uncertainty into exactly \
one of these diagnostic categories:

  COMPOUND: The requirement bundles multiple independent obligations that \
should be separated. Evidence: compound_obligation smells, low inter-dimension \
consistency, multiple distinct actors/actions.

  AMBIGUOUS: The requirement contains vague terms, multiple possible \
interpretations, or subjective criteria. Evidence: vague_term / weak_word \
smells, low clarity scores, unquantified terms.

  STRUCTURAL: The requirement conflicts with other requirements, system \
constraints, or architectural rules. Evidence: cross-requirement similarity \
hits, consistency issues, conflicting constraints.

  NOVEL: The requirement has no matching pattern in the knowledge base and \
deviates significantly from known exemplars. Evidence: very low retrieval \
similarity, no pattern matches, unfamiliar domain.

  INSUFFICIENT_EVIDENCE: The retrieval tools returned nothing relevant, so \
the agent had too little grounding to score confidently. Evidence: empty \
retrieval results, default/fallback scores.

Reply with a STRICT JSON object only:
{
  "category": str,
  "rationale": str,
  "supporting_evidence": [str, ...],
  "confidence": float
}"""


def build_categorize_prompt(
    requirement_text: str,
    traces: list[dict],
) -> str:
    traces_json = json.dumps(traces, indent=2, default=str)[:3000]
    return f"""Requirement:
\"\"\"{requirement_text}\"\"\"

Reasoning traces from Step 1 (GATHER):
{traces_json}

Classify the primary root cause of uncertainty. Pick the single category that \
best explains WHY the agent was uncertain. Return the JSON object."""


# ---------------------------------------------------------------------------
# Step 3 — CONSULT: formulate a targeted consultation question
# ---------------------------------------------------------------------------

CONSULT_SYSTEM = """\
You are the CONSULT step of the DART protocol. Based on the diagnostic \
hypothesis (category + rationale), formulate ONE targeted consultation \
question. This is NOT a re-vote — it is a specific, diagnostic question \
designed to resolve the identified uncertainty.

Category-specific question templates:
  COMPOUND → "Can these obligations be independently implemented and tested? \
List each distinct obligation and whether it needs its own requirement."
  AMBIGUOUS → "Which interpretation does the evidence support? What specific \
terms need defining and what measurable criteria could replace them?"
  STRUCTURAL → "Does this requirement conflict with [specific requirement]? \
Explain the constraint and which takes precedence."
  NOVEL → "What is the closest known pattern? How far does this requirement \
deviate, and is the deviation justified?"
  INSUFFICIENT_EVIDENCE → "What domain knowledge or standards apply to this \
requirement? What evidence would increase scoring confidence?"

Reply with a STRICT JSON object only:
{
  "target_agent": str,
  "question": str,
  "context": {},
  "category": str
}"""


def build_consult_prompt(
    requirement_text: str,
    hypothesis: dict,
    traces: list[dict],
) -> str:
    hyp_json = json.dumps(hypothesis, indent=2, default=str)[:1500]
    traces_summary = json.dumps(traces[:3], indent=2, default=str)[:2000]
    return f"""Requirement:
\"\"\"{requirement_text}\"\"\"

Diagnostic hypothesis from Step 2 (CATEGORIZE):
{hyp_json}

Key reasoning traces:
{traces_summary}

Formulate one targeted consultation question that will resolve this specific \
uncertainty. The question must be answerable with evidence, not opinion. \
Return the JSON object."""


# ---------------------------------------------------------------------------
# Step 4 — RESPOND: answer the consultation with evidence
# ---------------------------------------------------------------------------

RESPOND_SYSTEM = """\
You are the RESPOND step of the DART protocol. You receive a targeted \
consultation question from Step 3 and must answer it with EVIDENCE-BASED \
reasoning. Use domain knowledge (IEEE 830 standards, INVEST criteria, \
decomposition patterns) to ground your answer.

You are a different analytical perspective from the original agent. Your \
answer should add NEW information or a DIFFERENT interpretation, not simply \
agree with what was already concluded.

Reply with a STRICT JSON object only:
{
  "agent_name": "dart_consultant",
  "answer": str,
  "evidence": [str, ...],
  "confidence": float,
  "recommended_resolution": str
}"""


def build_respond_prompt(
    requirement_text: str,
    consultation: dict,
    source_stage: str,
    retrieval_context: list[dict] | None = None,
) -> str:
    q = consultation.get("question", "")
    category = consultation.get("category", "unknown")
    ctx = json.dumps(consultation.get("context", {}), indent=2, default=str)[:1000]

    retrieval_block = ""
    if retrieval_context:
        items = retrieval_context[:5]
        retrieval_block = "\n\nRelevant domain knowledge (retrieved):\n" + "\n".join(
            f"  - {r.get('text', r)}" for r in items
        )

    return f"""Requirement:
\"\"\"{requirement_text}\"\"\"

Consultation question (category: {category}):
{q}

Context from the original analysis ({source_stage}):
{ctx}{retrieval_block}

Answer the consultation question with evidence. If the category is AMBIGUOUS, \
identify the specific vague terms and propose measurable replacements. If \
COMPOUND, list each distinct obligation. If STRUCTURAL, identify the conflict. \
If NOVEL, describe the closest known pattern.

Return the JSON object."""


# ---------------------------------------------------------------------------
# Step 5 — RESOLVE: select resolution action + actionable feedback
# ---------------------------------------------------------------------------

RESOLVE_SYSTEM = """\
You are the RESOLVE step of the DART protocol. Given the full diagnostic \
chain (traces, hypothesis, consultation question, consultation response), \
select one resolution action and produce actionable feedback for the student.

Resolution actions:
  RESOLVE: The diagnosis converges — produce final, actionable feedback \
telling the student exactly what to fix.
  RETRIEVE: Evidence is still thin — recommend expanding the retrieval scope \
and re-analyzing (only if iteration < 2).
  REFINE: The consultation response revealed a new aspect not covered by the \
original analysis — route back for re-analysis (only if iteration < 2).
  ESCALATE: The issue is unresolvable by the agents — route to the instructor \
for human judgment.

Rules:
  - RETRIEVE and REFINE are only available when dart_iteration < 2.
  - If dart_iteration >= 2, you MUST choose RESOLVE or ESCALATE.
  - NOVEL with confidence_agreement < 40 → force ESCALATE.
  - Always include actionable_feedback — never leave it empty.

Reply with a STRICT JSON object only:
{
  "action": str,
  "rationale": str,
  "evidence_summary": [str, ...],
  "confidence_agreement": float,
  "actionable_feedback": str
}"""


def build_resolve_prompt(
    requirement_text: str,
    hypothesis: dict,
    consultation: dict,
    response: dict,
    traces: list[dict],
    dart_iteration: int,
) -> str:
    hyp_json = json.dumps(hypothesis, indent=2, default=str)[:1000]
    cons_q = consultation.get("question", "")
    resp_json = json.dumps(response, indent=2, default=str)[:1500]
    traces_summary = json.dumps(traces[:3], indent=2, default=str)[:1500]

    iteration_note = ""
    if dart_iteration >= 2:
        iteration_note = (
            "\n\nIMPORTANT: This is iteration 2+ — RETRIEVE and REFINE are "
            "no longer available. You MUST choose RESOLVE or ESCALATE."
        )

    return f"""Requirement:
\"\"\"{requirement_text}\"\"\"

Diagnostic hypothesis:
{hyp_json}

Consultation question:
{cons_q}

Consultation response:
{resp_json}

Original reasoning traces:
{traces_summary}

Current DART iteration: {dart_iteration}{iteration_note}

Select a resolution action and produce actionable feedback for the student. \
The feedback should be specific, pedagogical, and tell the student exactly \
what to change. Return the JSON object."""

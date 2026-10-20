# Adaptive AI Tutor Agent

Owner: Adaptive Tutor team member. All tutor logic lives in this directory.

**The Adaptive AI Tutor is ONE agent.** It has one entry point (`agent.py`) registered with the
orchestrator. Its internal parts are modules of this agent, not separate agents and not a
sub-orchestrator. Modules are plain Python packages: they define no agent classes, are not
registered in `app/agents/registry.py`, and never route requests between themselves.

## Contract

- Implement an agent class with `name = AgentName.ADAPTIVE_TUTOR` and
  `async def handle(request: AgentRequest) -> AgentResponse` (see `app/agents/base.py`).
- Actions use the `tutor.` prefix (e.g. `tutor.chat`, `tutor.sprint_guidance`,
  `tutor.generate_assessment`); the orchestrator routes them here.
- Tutor-specific models go in `schemas.py`.
- Never import or call another agent; return a `NextAction` instead.
- When ready, register the agent in `app/agents/registry.py`.

## Shared code and infrastructure

- Reuse the shared contracts from `shared.contracts` (`AgentRequest`, `AgentResponse`,
  `SelviaContext`, `Evidence`, `NextAction`, ...). Do not copy or fork them here; tutor-specific
  shapes travel in `AgentRequest.input` and `AgentResponse.result`. A field several agents need is
  a change to `backend/shared/`, made through review.
- Do not build private Neo4j, database or MCP clients inside this directory. Neo4j access belongs
  in the shared knowledge graph layer, external systems (MCP) in `app/integrations/`, and
  persistence in the Core API (`backend/server`). Tutor modules use those shared layers.

## Internal layout

```text
adaptive_tutor/
  agent.py          the single agent entry point (AdaptiveTutorAgent.handle)
  schemas.py        tutor-specific models
  context/          student and project context for the request
  knowledge/        required knowledge for the current task (via the shared knowledge graph)
  evidence/         retrieval and normalization of student learning evidence
  competency/       competency estimation and knowledge-gap analysis
  decision/         Adaptive Decision Engine
  intervention/     delivery of the selected intervention's content
  assessment/       adaptive assessment and reassessment
  adaptation/       learning momentum and the adaptation loop
  tests/            tests for this agent
```

| Module | Responsibility |
|---|---|
| `context/` | Obtain and validate the student, project, sprint and task the request is about. |
| `knowledge/` | Identify the concepts a project task requires, from validated course knowledge and task-to-concept mappings, not generated freely. |
| `evidence/` | Retrieve learning evidence (quizzes, exercises, assessments, attempts) and normalize it into consistent internal structures. Missing evidence is not zero competency. |
| `competency/` | Estimate competency per required concept, keep confidence separate from the estimate, and identify knowledge gaps against the task's requirement. |
| `decision/` | **Adaptive Decision Engine**, the main research contribution: selects the next learning intervention and explains why. |
| `intervention/` | Produce the content for the intervention the engine selected (explanations, examples, exercises, guidance). An LLM may generate content but does not decide competency or the intervention. |
| `assessment/` | Adaptive assessment and reassessment that produce new evidence. |
| `adaptation/` | Learning momentum and the loop that recalculates competency and the recommendation after new evidence. |
| `tests/` | Tests for this agent; run with `uv run pytest` from `backend/agentic_framework/`. |

### Adaptive Decision Engine (`decision/`)

The engine is the central research mechanism of this agent. It selects the next intervention from
the project and task context, required knowledge, student evidence, estimated competency and gaps,
and learning momentum when available:

```text
D_t = f(P_t, K_t, E_t, C_t, M_t)
```

It is a research model to be developed and evaluated, not a validated algorithm. Competency
estimation stays in `competency/`; the engine consumes its output and does not estimate
competency itself. Every decision returns the target concept, the selected action and the reasons
behind it.

### Adaptation loop

```text
Project task -> required knowledge -> evidence -> competency and gaps -> decision
  -> intervention -> student activity -> new evidence -> recalculated competency
  -> updated recommendation
```

## Status

Implemented so far: `schemas.py`, `context/` (Student & Project Context), `evidence/` (normalizer
and fixtures), `knowledge/` (Required Knowledge Identification via Neo4j + OpenAI), `competency/`
(classic BKT mastery from chronological performance evidence; baseline params, not trained),
`agent.py` (`tutor.chat` + `tutor.identify_required_knowledge`), and unit tests for those pieces.

`tutor.identify_required_knowledge` resolves `course_id` from request input or the sprint project's
`course_id`, loads assigned tasks from the sprint provider, retrieves course-scoped concepts from
the shared `app/knowledge_graph` Neo4j layer, selects baseline lexical candidates (not vector RAG),
and asks OpenAI to choose Neo4j concept IDs only from those candidates.

`competency.estimate_concept_mastery_bkt` consumes normalized performance evidence (fixtures or MCP
records) plus a trusted `student_id`. Missing usable evidence returns `mastery_probability=None`
(not zero). Learning-behaviour activities are excluded from BKT.

`tutor.estimate_competency` integrates required-knowledge (when `concept_ids` omitted), MCP or
inline `performance_evidence`, and BKT. Sprint fixtures use the live SLAP student/course IDs for
end-to-end smoke (`scripts/smoke_tutor_pipeline.py`).

Decision, intervention, assessment, and adaptation modules remain unimplemented.
The Core API public tutor route stays fail-closed until end-to-end readiness is reviewed separately.

External learning-platform MCP access belongs in
`app/integrations/selvia_tutor_mcp/` (shared client + `RequestScopedTutorTokenProvider`).
Do not put `MCP_TUTOR_TOKEN_SECRET` in this agent.

See `docs/TEAM_DEVELOPMENT_GUIDE.md`.

# Adaptive AI Tutor Agent

Owner: Adaptive Tutor team member. All tutor logic lives in this directory.

**The Adaptive AI Tutor is ONE agent.** It has one entry point (`agent.py`) registered with the
orchestrator. Its internal parts are modules of this agent, not separate agents and not a
sub-orchestrator.

## Contract

- Implement an agent class with `name = AgentName.ADAPTIVE_TUTOR` and
  `async def handle(request: AgentRequest) -> AgentResponse` (see `app/agents/base.py`).
- Actions use the `tutor.` prefix (e.g. `tutor.chat`, `tutor.sprint_guidance`,
  `tutor.generate_assessment`); the orchestrator routes them here.
- Tutor-specific models go in `schemas.py`.
- Never import or call another agent; return a `NextAction` instead.
- When ready, register the agent in `app/agents/registry.py`.

## Suggested internal layout

```text
adaptive_tutor/
  agent.py          the single agent entry point
  schemas.py
  modules/          internal modules of this one agent
    context/                      student & project context
    knowledge_identification/     required knowledge for the current task
    course_graph/                 course knowledge graph access
    student_graph/                student knowledge graph access
    evidence/                     evidence collector
    learner_model/
    decision_engine/              adaptive decision engine
    assessment/                   assessment generator
    feedback/                     feedback & reflection
    adaptation/                   adaptation loop
```

See `docs/TEAM_DEVELOPMENT_GUIDE.md`.

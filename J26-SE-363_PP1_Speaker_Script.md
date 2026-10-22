# J26-SE-363 — PP1 Speaker Script

**Timing:** Part 1 (overall) ≈ 5 min · Part 2 ≈ 2 min per member. Scripts are also embedded in each slide's PowerPoint speaker notes (Presenter View).

---

### Slide 1 — Cover

Good morning. We are group J26-SE-363, presenting Progress Presentation 1 on a multi-agent generative-AI framework that supports software-engineering project-based learning and lecturer monitoring. I am [your name]; with me are my team members. Our supervisor is Dr. Kalpani Manathunga and our co-supervisor is Ms. Aparna Jayawardane. Over the next five minutes we cover the overall project, then each of us presents our individual component for two minutes. (~20s)

### Slide 2 — Proposal Feedback → Action

At the proposal viva the panel’s main challenge was whether this is genuinely multi-agent or just static workflows. We now define each component as an autonomous agent with its own goal, tools, memory and decision-making, coordinated over a message bus — the architecture slide makes that explicit. We also added a concrete validation plan, scoped MCP to controlled tool access, clarified the LLM-as-Judge placement, and rebuilt the deck to be explained rather than read. (~45s)

### Slide 3 — Problem & Impact

Team software-engineering projects break down in four recurring ways. First, students write untestable requirements and plan poorly. Second, they have no context-aware help when they hit blockers. Third, team grading hides who actually did the work. Fourth, security is barely assessed, so vulnerabilities ship. The impact compounds across every team: lower learning quality, unfair accountability, and graduates who are less industry-ready. (~50s)

### Slide 4 — Stakeholders & Beneficiaries

Three groups feel this problem. Students face unguided planning and unfair grading, and gain context-aware support and fairer, evidence-based grades. Instructors carry a heavy monitoring load and struggle to assess individuals; they gain automated Git and Scrum evidence and faster decisions. Higher-ed and industry struggle with grading scale and weak security focus, and benefit from scalable, objective evaluation and security-aware, industry-ready graduates. (~40s)

### Slide 5 — Design Excellence of the Solution

Our solution is one coordinated framework of four autonomous agents — requirements and planning, adaptive tutor, performance assessment, and security — that communicate over an agent message bus. Crucially, they all read and write a single shared project context: requirements, plans, sprint tasks, GitHub activity, source code, docs and assessment data. That shared context is what makes the framework integrated, context-aware, evidence-based and scalable — and what distinguishes true agents from isolated scripts. (~55s)

### Slide 6 — Live Demo (placeholder)

Here is a short demo of the current prototype. [Play the 1–2 minute video, or ask the panel to scan the QR code.] Replace the placeholder with your final video link and generated QR before the viva. (~20s)

### Slide 7 — Part 2 — Divider

That completes the overall project. We now move to the individual components — two minutes each, in this order: requirements and planning, performance assessment, adaptive tutor, and security.

### Slide 8 — Rajapaksha · Intro

My component improves requirement quality and project planning. Students often write untestable requirements and plan without proper decomposition. My agents analyse requirement quality, decompose work, and estimate effort. The novelty is DART — a Diagnostic Arbitration Routing Technique that decides which specialist agent should handle each diagnostic. (~40s)

### Slide 9 — Rajapaksha · Overview

The sub-problem is weak requirements and planning. I meet user needs with testable-requirement checks, structured decomposition and industry-style effort estimation. The design excellence is DART arbitration plus a quality gate that blocks weak requirements before planning — and, answering the panel, these are autonomous agents with their own tools and decisions, not static workflows. So far the quality and decomposition agents are prototyped, DART routing is defined, and I validate against the TAWOS dataset. (~80s across these two slides)

### Slide 10 — Rajapaksha · DART Diagram

This is the flow. A student requirement enters the DART router, which performs diagnostic arbitration — deciding which specialist agent handles each issue. The Quality Agent validates testable requirements as a quality gate, the Decomposition Agent breaks work into structured tasks, and the Effort Estimation Agent predicts effort and story points. The output is a planning-ready, testable requirement set. The key point for the panel: these are autonomous agents coordinated by DART, not a fixed script. (~40s)

### Slide 11 — Kumbukage · Intro

My component is automated individual performance assessment. Team grading hides who actually did the work. I mine Git and Scrum evidence across seven standardized factors and add active code-comprehension probes. The novelty is hybrid passive–active assessment: passive mining shows what was contributed, active probing shows whether the student understands it. (~40s)

### Slide 12 — Kumbukage · Overview

The sub-problem is that team grades mask individuals. I meet the need for a fair, explainable per-student grade built from GitHub and Scrum evidence, with the instructor as final decision-maker. The design excellence is the seven-factor model with cohort standardization and learned weights, plus a code-ownership probe using Tree-sitter and CodeBERT at r=0.81. The UI, comprehension interface and dashboard are built; the mining pipeline and models are in progress. On the panel’s point, LLM-as-Judge is used specifically for requirement–code semantic alignment. (~80s)

### Slide 13 — Kumbukage · 7-Factor Pipeline

The pipeline mines evidence from GitHub and Scrum, extracts structured feature vectors, scores seven performance factors — effort, consistency, requirement fulfillment, collaboration, task complexity, behavioral pattern, and the novel code-ownership factor — then synthesizes them. We standardize each factor with a z-score, fuse them with empirically learned weights, and produce an explainable individual score with a full breakdown. (~40s)

### Slide 14 — Ekanayake · Intro

My component is an adaptive AI tutor. Software-engineering students have continuously changing needs, and current tutors give generic or fragmented help. My tutor builds an evolving, multi-dimensional learner model and uses it to decide the next intervention. The novelty is continuous multi-dimensional personalization across learning, guidance and assessment. (~40s)

### Slide 15 — Ekanayake · Overview

The sub-problem is fragmented personalization. I meet the need for personalized learning paths, project-aware sprint guidance and adaptive quizzes. The learner state combines knowledge, assessment, behaviour, trends and project context, modelled with Neo4j knowledge graphs and Bayesian Knowledge Tracing, with RAG-grounded content. The learner model and graph schema are designed and the adaptation engine is in progress. Answering the panel, I added a concrete validation plan — pre/post gains, adaptive-vs-non-adaptive, AUC/F1/RMSE — and scoped MCP to controlled tool and data access. (~80s)

### Slide 16 — Ekanayake · Learner-Model Loop

Evidence from learning activity, assessment, behaviour and project context feeds a dynamic learner model built on Neo4j knowledge graphs and Bayesian Knowledge Tracing. That evolving, multi-dimensional state drives three adaptive outputs: personalized learning paths, project-aware guidance, and adaptive assessment. It is a continuous loop — each interaction updates the model and changes the next intervention. (~40s)

### Slide 17 — Croos · Intro

My component is the security-aware subsystem. Today, scanners report code, dependency and secret issues separately, with no link to the project, and the framework itself reads untrusted repository text. I detect vulnerabilities, trace each to its owner, and protect the agents. The novelty is project-context traceability combined with hybrid deterministic and semantic detection. (~40s)

### Slide 18 — Croos · Overview

The sub-problem is isolated, untraceable findings and unsafe agents. I meet the need for prioritized findings linked to requirement, sprint, commit and student, with evidence-backed fixes and verified closure on a lecturer dashboard. The design excellence is that deterministic scanners supply the evidence while the LLM only explains and prioritizes, plus governance that protects every agent. Literature review and scope are complete and the threat model is in progress. On the panel’s point, this is genuinely multi-agent — separate detection, understanding and governance agents. (~80s)

### Slide 19 — Croos · Detect→Understand→Act

The subsystem works in three agent stages. Detect: deterministic scanners — CodeQL, dependency and secret scanning — collect normalized evidence. Understand: only relevant code reaches the LLM, which confirms exploitability, maps each finding to its requirement, commit and owner, and builds a comprehension probe. Act: it scores risk, gives an evidence-backed fix, shows a lecturer dashboard, and verifies closure by re-scanning. Scanners decide what is real; the model decides what it means and how to fix it. These are distinct, coordinated agents — which answers the panel’s multi-agent question. (~40s)

### Slide 20 — Business View (overall)

Commercially this is a B2B EdTech SaaS. The buyers are deans, department heads and module leaders managing large cohorts with departmental budgets. The market is higher-ed CS and SE programs worldwide, plus bootcamps and corporate upskilling. What is unique is the coordinated framework — DART arbitration, seven-factor explainable scoring with the ownership probe, and project-context security traceability. Cost is recovered through tiered SaaS pricing at over 75% gross margin, breaking even within 18–24 months across 8–10 university pilots. (~45s)

### Slide 21 — Thank You / Q&A

Thank you. We are happy to take questions.

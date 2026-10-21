import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import bundle from '../demo/demoBundle.json'
import { AgentsBody } from '../pages/AgentsPage.jsx'
import { AuditTable, DecisionTrail, GovernancePanel } from './AgentParts.jsx'
import WorkflowDiagram from './WorkflowDiagram.jsx'
import { trailAgents } from '../lib/agents.js'

const FULL = 'sample-python-demo'
const NO_LLM = 'sample-python-no-llm'
const HOSTILE = 'sample-hostile-readme'
const html = (element) => renderToStaticMarkup(<MemoryRouter>{element}</MemoryRouter>)
const agents = (run) => bundle.agents[run]
const workflow = (run) => bundle.workflow[run]
const withQuery = (element) => html(<QueryClientProvider client={new QueryClient()}>{element}</QueryClientProvider>)
const body = (run, role, extra) => withQuery(<AgentsBody agents={agents(run)} workflow={workflow(run)} role={role} team="J26-SE-363" run={run} {...extra} />)

describe('decision trails', () => {
  it('highlights a rejected choice and says what was proposed and why it was refused', () => {
    const agent = trailAgents(agents(HOSTILE).decision_trail)[0]
    const markup = html(<DecisionTrail agent={agent} />)
    expect(markup).toContain('data-rejected="true"')
    expect(markup).toContain('border-l-destructive')
    expect(markup).toContain('REJECTED CHOICE.')
    expect(markup).toContain('shell:rm -rf /')
    expect(markup).toContain('not one of the valid options')
    expect(markup).toContain('The rules decided instead.')
    expect(markup).toContain('1 rejected choice<')
  })

  it('shows an ordinary decision as an ordinary row, with what it could choose, what it chose and why', () => {
    const agent = trailAgents(agents(FULL).decision_trail)[0]
    const markup = html(<DecisionTrail agent={agent} />)
    expect(markup).toContain('data-rejected="false"')
    expect(markup).not.toContain('REJECTED CHOICE')
    expect(markup).toContain('goal met: every category is FULL')
    expect(markup).toContain('0 rejected choices')
    expect(markup).toContain('Goal: A findings report where every category is covered')
  })

  it('shows every question-agent decision, one row per step', () => {
    const agent = trailAgents(agents(FULL).decision_trail)[1]
    expect(html(<DecisionTrail agent={agent} />).match(/data-step=/g)).toHaveLength(agent.entries.length)
  })

  it('can show only the rejected choices, and says when an agent has none', () => {
    const hostile = trailAgents(agents(HOSTILE).decision_trail)
    const gov = html(<DecisionTrail agent={hostile[2]} onlyRejected />)
    expect(gov).toContain('No choice of this agent was rejected.')
    const only = html(<DecisionTrail agent={hostile[1]} onlyRejected />)
    expect(only.match(/data-rejected="true"/g)).toHaveLength(3) // the policy was refused on its first three decisions
    expect(only.match(/data-step=/g)).toHaveLength(3) // and only those rows are listed
    expect(html(<DecisionTrail agent={hostile[1]} />).match(/data-step=/g)).toHaveLength(hostile[1].entries.length)
    expect(html(<DecisionTrail agent={{ ...hostile[0], entries: [] }} />)).toContain('made no decision in this run')
  })
})

describe('the governance panel', () => {
  it('shows the level, score, second checks and escalation of a hostile repository, and labels every indicator "indicator, not proof"', () => {
    const markup = html(<GovernancePanel governance={agents(HOSTILE).governance} />)
    expect(markup).toContain('scrutiny elevated')
    expect(markup).toMatch(/data-fact="score"[^>]*>.*?5 \(elevated at 3, high at 6\)/)
    expect(markup).toMatch(/data-fact="second-checks"[^>]*>.*?16/)
    expect(markup).toMatch(/data-fact="escalation"[^>]*>.*?No/)
    expect(markup).toContain('data-slot="indicators"')
    const rows = markup.match(/data-pattern=/g)
    expect(rows).toHaveLength(agents(HOSTILE).governance.injection_indicators.length)
    expect(markup.match(/indicator, not proof/g).length).toBeGreaterThanOrEqual(rows.length + 1)
    expect(markup).toContain('README.md')
    expect(markup).toContain('ignore-previous-instructions')
    expect(markup).toContain('nothing was blocked or changed')
    expect(markup).toContain('data-slot="scrutiny-history"')
    expect(markup).toContain('normal → elevated')
  })

  it('does not call a repository clean when nothing was found', () => {
    const markup = html(<GovernancePanel governance={agents(FULL).governance} />)
    expect(markup).toContain('scrutiny normal')
    expect(markup).not.toContain('data-pattern=')
    expect(markup).toMatch(/No indicator was found in the 4 README and commit-message sources/)
    expect(markup).toContain('heuristic check: it is indicator, not proof that the repository is clean')
  })

  it('shows an escalation for human review when there is one', () => {
    const g = { ...agents(HOSTILE).governance, scrutiny: { ...agents(HOSTILE).governance.scrutiny, level: 'high', escalated: true, escalation_reason: 'score 7 reached 6' } }
    const markup = html(<GovernancePanel governance={g} />)
    expect(markup).toContain('scrutiny high')
    expect(markup).toContain('Yes: score 7 reached 6')
    expect(markup).toContain('flagged for human review')
  })

  it('says so when there is no governance record', () => {
    expect(html(<GovernancePanel governance={null} />)).toContain('No governance record in this run.')
  })
})

describe('the audit table', () => {
  const audit = bundle.audit[HOSTILE]

  it('shows lines with facts and hashes cut short, never a full hash', () => {
    const markup = html(<AuditTable lines={audit.lines} total={audit.total} />)
    expect(markup).toContain('Audit log (hashes only)')
    expect(markup).toContain('data-hash="true"')
    const full = audit.lines.find((l) => l.prompt_sha256).prompt_sha256
    expect(markup).not.toContain(full)
    expect(markup).toContain(`${full.slice(0, 12)}…`)
    expect(markup).toContain(`of ${audit.total}`)
    expect(markup.match(/data-seq=/g)).toHaveLength(25)
    expect(markup).toContain('Visible to lecturers and administrators only.')
  })

  it('has no prompt text, e-mail address, path or secret in it', () => {
    const markup = html(<AuditTable lines={audit.lines} total={audit.total} />)
    expect(markup).not.toMatch(/[\w.+-]+@[\w-]+\.[a-z]{2,}/i)
    expect(markup).not.toMatch(/[A-Z]:\\|\/Users\/|AKIA[0-9A-Z]{16}/)
    expect(markup).not.toMatch(/NOTE FOR AI TOOLS/)
  })
})

describe('the page for each role', () => {
  it('does not render the audit log at all for a student', () => {
    const markup = body(HOSTILE, 'student')
    expect(markup).not.toContain('data-slot="audit"')
    expect(markup).not.toContain('Audit log')
    expect(markup).not.toContain('audit.jsonl')
    expect(markup).not.toContain('hashes only')
    expect(markup).toContain('data-slot="governance"')
    expect(markup).toContain('data-slot="trails"')
    expect(markup).toContain('data-slot="workflow-diagram"')
  })

  it('has a place for the audit log for a lecturer and an administrator, and none for no role', () => {
    // the log itself is fetched by a query mounted only for these roles, so a static render shows its loading state, not the table
    for (const role of ['instructor', 'admin']) expect(body(HOSTILE, role).split('data-slot="workflow-card"')[1]).toMatch(/data-slot="card"|animate-pulse|skeleton/i)
    expect(body(HOSTILE, null).split('data-slot="workflow-card"')[1]).not.toMatch(/animate-pulse|skeleton/i)
  })

  it('shows the same governance and trails to every role', () => {
    const strip = (m) => m.split('data-slot="workflow-card"')[0]
    expect(strip(body(HOSTILE, 'student'))).toBe(strip(body(HOSTILE, 'instructor')))
  })
})

describe('the workflow diagram', () => {
  const nodeStatus = (markup, id) => new RegExp(`data-node="${id}" data-status="([^"]*)"`).exec(markup)?.[1]

  it('draws every stage of the workflow, coloured by what happened in the run', () => {
    const markup = html(<WorkflowDiagram workflow={workflow(NO_LLM)} />)
    for (const id of ['fetch', 'scan', 'governance', 'interpret', 'trace', 'risk', 'guidance', 'questions', 'report']) expect(markup).toContain(`data-node="${id}"`)
    expect(nodeStatus(markup, 'scan')).toBe('completed')
    expect(nodeStatus(markup, 'interpret')).toBe('skipped')
    expect(nodeStatus(markup, 'questions')).toBe('skipped')
    expect(nodeStatus(markup, 'report')).toBe('completed')
    const skipped = /data-node="interpret"[\s\S]*?<rect[^>]*class="([^"]*)"/.exec(markup)[1]
    const done = /data-node="scan"[\s\S]*?<rect[^>]*class="([^"]*)"/.exec(markup)[1]
    expect(skipped).toContain('dasharray')
    expect(done).not.toContain('dasharray')
    expect(skipped).not.toEqual(done)
  })

  it('shows a failed stage in red', () => {
    const w = { ...workflow(FULL), ran: { ...workflow(FULL).ran, workflow: { ...workflow(FULL).ran.workflow, risk: 'failed' } } }
    const markup = html(<WorkflowDiagram workflow={w} />)
    expect(nodeStatus(markup, 'risk')).toBe('failed')
    expect(/data-node="risk"[\s\S]*?<rect[^>]*class="([^"]*)"/.exec(markup)[1]).toContain('red')
  })

  it('offers to open the agent graphs under their nodes, closed at first', () => {
    const markup = html(<WorkflowDiagram workflow={workflow(FULL)} />)
    for (const id of ['scan', 'interpret', 'trace', 'questions']) expect(markup).toMatch(new RegExp(`data-node="${id}"[^>]*role="button"[^>]*aria-expanded="false"`))
    expect(markup).not.toContain('data-nested=')
    expect(markup).not.toMatch(/data-node="fetch"[^>]*role="button"/)
  })

  it('expands the nested graph under its node, with its own nodes coloured by whether they ran', () => {
    const markup = html(<WorkflowDiagram workflow={workflow(FULL)} initiallyExpanded={['scan', 'questions']} />)
    expect(markup).toContain('data-nested="orchestrator"')
    expect(markup).toContain('data-nested="question"')
    expect(markup).not.toContain('data-nested="governance"')
    const question = markup.split('data-nested="question"')[1]
    for (const id of ['ask', 'score', 'follow_up', 'close', 'escalate']) expect(question).toContain(`data-node="${id}"`)
    expect(question).toMatch(/data-node="escalate" data-status="ran"/)
    expect(markup).toMatch(/data-node="scan"[^>]*aria-expanded="true"/)
    expect(markup).toContain('Question Agent (inside Questions (mock Tutor))')
    expect(question).toContain('data-kind="loop"') // the follow-up loop is drawn
  })

  it('shows which nodes of an agent did not run', () => {
    const markup = html(<WorkflowDiagram workflow={workflow(NO_LLM)} initiallyExpanded={['questions']} />)
    expect(markup.split('data-nested="question"')[1]).toMatch(/data-node="ask" data-status="not run"/)
  })

  it('keeps the nested graph inside the drawing and moves later rows down to make room', () => {
    const closed = html(<WorkflowDiagram workflow={workflow(FULL)} />)
    const open = html(<WorkflowDiagram workflow={workflow(FULL)} initiallyExpanded={['scan']} />)
    const h = (m) => Number(/viewBox="0 0 [\d.]+ ([\d.]+)"/.exec(m)[1])
    expect(h(open)).toBeGreaterThan(h(closed))
    const w = Number(/viewBox="0 0 ([\d.]+) /.exec(open)[1])
    const nestedX = Number(/data-nested="orchestrator"[^>]*transform="translate\(([\d.]+) /.exec(open)[1])
    expect(nestedX).toBeGreaterThan(0)
    expect(nestedX).toBeLessThan(w)
  })

  it('has a legend, an accessible name and the Mermaid source', () => {
    const markup = html(<WorkflowDiagram workflow={workflow(FULL)} />)
    expect(markup).toContain('role="img"')
    expect(markup).toContain('aria-label="The Security Assistant workflow')
    expect(markup).toContain('data-slot="legend"')
    expect(markup).toContain('dashed arrow: conditional edge')
    expect(markup).toContain('data-slot="mermaid-source"')
    expect(markup).toContain('graph TD;')
  })

  it('says when the diagram files are missing instead of drawing nothing', () => {
    const missing = { graphs: { workflow: { nodes: [], edges: [], mmd: null } }, ran: { workflow: {} } }
    expect(html(<WorkflowDiagram workflow={missing} />)).toContain('data-slot="diagram-missing"')
  })

  it('shows no name, e-mail address, path or secret', () => {
    const markup = body(HOSTILE, 'instructor', { initiallyExpanded: ['scan', 'interpret', 'questions'] }) + body(FULL, 'student')
    expect(markup).not.toMatch(/[\w.+-]+@[\w-]+\.[a-z]{2,}/i)
    expect(markup).not.toMatch(/[A-Z]:\\|\/Users\/|AKIA[0-9A-Z]{16}/)
    expect(markup).not.toMatch(/Jane|Eric/)
  })
})

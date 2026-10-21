import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Checkbox } from '@/components/ui/checkbox'
import QueryBoundary from '@/shared/components/QueryBoundary.jsx'
import AssistantFrame from '../components/AssistantFrame.jsx'
import { AuditTable, DecisionTrail, GovernancePanel } from '../components/AgentParts.jsx'
import { DiagramCard } from '../components/WorkflowDiagram.jsx'
import { useAgents, useAudit, useWorkflow } from '../hooks/useSecurityAssistant.js'
import { canSeeAudit, trailAgents } from '../lib/agents.js'

// Mounted only for a lecturer or an administrator: a student's page never asks for the audit log and has no place for it.
function AuditSection({ team, run }) {
  const query = useAudit(team, run)
  return (
    <QueryBoundary query={query} variant="card" count={1}>
      {(audit) => <AuditTable lines={audit.lines} total={audit.total} />}
    </QueryBoundary>
  )
}

export function AgentsBody({ agents, workflow, role, team, run, initiallyExpanded }) {
  const [onlyRejected, setOnlyRejected] = useState(false)
  return (
    <div className="space-y-4">
      <GovernancePanel governance={agents.governance} />

      <section className="space-y-3" data-slot="trails">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">Decision trails</h2>
            <p className="text-xs text-muted-foreground">
              Each agent picks its next action from a fixed list. A choice outside the list is refused by the code, shown here as a rejected choice, and the rules decide instead.
            </p>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={onlyRejected} onCheckedChange={(v) => setOnlyRejected(Boolean(v))} aria-label="Only rejected choices" />
            Only rejected choices
          </label>
        </div>
        {trailAgents(agents.decision_trail).map((agent) => (
          <DecisionTrail key={agent.key} agent={agent} onlyRejected={onlyRejected} />
        ))}
      </section>

      <DiagramCard workflow={workflow} initiallyExpanded={initiallyExpanded} />

      {canSeeAudit(role) ? <AuditSection team={team} run={run} /> : null}
    </div>
  )
}

function Loaded({ selection, team, role }) {
  const agentsQuery = useAgents(team, selection.run)
  const workflowQuery = useWorkflow(team, selection.run)
  const [params] = useSearchParams()
  const expand = (params.get('expand') || '').split(',').filter(Boolean) // ?expand=scan,questions opens those nodes' graphs
  return (
    <QueryBoundary query={[agentsQuery, workflowQuery]} variant="card" count={3}>
      {([agents, workflow]) => <AgentsBody agents={agents} workflow={workflow} role={role} team={team} run={selection.run} initiallyExpanded={expand} />}
    </QueryBoundary>
  )
}

export default function AgentsPage() {
  return (
    <AssistantFrame
      title="Agents and governance"
      description="How the three agents decided, what the governance gate did, and which parts of the workflow ran."
      howToRead="Governance first (the level and any indicator, which is not proof), then each agent's decisions (a red row is a choice the code refused), then the diagram: colour is what happened to each stage in this run."
    >
      {(context) => <Loaded {...context} />}
    </AssistantFrame>
  )
}

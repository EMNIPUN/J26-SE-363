import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CheckCircle2 } from 'lucide-react'
import PageHeader from '@/shared/components/PageHeader.jsx'
import QueryBoundary from '@/shared/components/QueryBoundary.jsx'
import { Card } from '@/components/ui/card'
import { useScope } from '@/shared/context/useScope.js'
import { useSecurityFindings } from '../hooks/useSecurityFindings.js'
import { PriorityBadge, StatusBadge, ConfidenceBadge } from '../components/FindingBadges.jsx'

export default function Remediation() {
  const findingsQuery = useSecurityFindings()

  return (
    <div className="space-y-6 animate-fade-rise">
      <PageHeader
        title="Remediation"
        breadcrumb={['Project Security', 'Remediation']}
        description="Select a finding to open its evidence-grounded fix guidance. A finding closes only once a Tutor-verified learning check confirms understanding — not just that the line was deleted."
      />

      <QueryBoundary query={findingsQuery} variant="card" count={2}>
        {(findings) => <RemediationList findings={findings} />}
      </QueryBoundary>
    </div>
  )
}

function RemediationList({ findings }) {
  const { teamId } = useParams()
  const { selectedGroup } = useScope()
  const teamCode = selectedGroup?.code || teamId || 'J26-SE-363'

  const remediableFindings = useMemo(() => findings.filter((f) => f.status !== 'closed'), [findings])

  if (remediableFindings.length === 0) {
    return (
      <Card className="p-8 text-center bg-card border-border shadow-xs">
        <CheckCircle2 className="h-8 w-8 text-emerald-500 mx-auto mb-3" />
        <p className="text-sm font-semibold text-foreground">Nothing left to remediate</p>
        <p className="text-xs text-muted-foreground mt-1">
          Every finding has been fixed and Tutor-verified closed.
        </p>
      </Card>
    )
  }

  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
        Findings to remediate
      </h3>
      <div className="space-y-2">
        {remediableFindings.map((f) => (
          <Link key={f.id} to={`/teams/${teamCode}/security/remediation/${f.id}`}>
            <Card className="p-4 bg-card border-border shadow-xs cursor-pointer card-hover-lift">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <PriorityBadge priority={f.priority} />
                    <span className="text-[11px] text-muted-foreground">{f.cwe}</span>
                  </div>
                  <p className="text-sm font-semibold text-foreground truncate">{f.title}</p>
                  <p className="text-[11px] text-muted-foreground font-mono truncate">
                    {f.file}
                    {f.line ? `:${f.line}` : ''}
                    {f.endpoint ? ` • ${f.endpoint}` : ''}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <ConfidenceBadge confidence={f.confidence} />
                  <StatusBadge status={f.status} />
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}

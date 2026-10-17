import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ShieldAlert,
  ShieldCheck,
  Gauge,
  GraduationCap,
  ChevronRight,
  ScanSearch,
  Wrench,
} from 'lucide-react'
import PageHeader from '@/shared/components/PageHeader.jsx'
import StatCard from '@/shared/components/StatCard.jsx'
import QueryBoundary from '@/shared/components/QueryBoundary.jsx'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useScope } from '@/shared/context/useScope.js'
import { useSecurityFindings } from '../hooks/useSecurityFindings.js'
import { CATEGORY_OPTIONS } from '../data/mockFindings.js'
import { PriorityBadge, StatusBadge } from '../components/FindingBadges.jsx'

const SDLC_PHASES = [
  { phase: 'Requirements', detail: 'STRIDE threat annotation on user stories & architecture docs', covered: true },
  { phase: 'Implementation', detail: 'CodeQL, Gitleaks/TruffleHog, OSV-Scanner on source & history', covered: true },
  { phase: 'Testing', detail: 'LLM triage, traceability mapping, risk prioritisation', covered: true },
  { phase: 'Deployment', detail: 'GitHub Actions workflow linter against the CI/CD checklist', covered: true },
]

export default function Dashboard() {
  const { teamId } = useParams()
  const { selectedGroup } = useScope()
  const teamCode = selectedGroup?.code || teamId || 'J26-SE-363'
  const findingsQuery = useSecurityFindings()

  return (
    <div className="space-y-6 animate-fade-rise">
      <PageHeader
        title="AEGIS Security Dashboard"
        breadcrumb={['Project Security', 'Dashboard']}
        description={`Deterministic-scanner-first vulnerability overview for ${selectedGroup?.projectTitle || teamCode}, classified by OWASP category and project-context risk.`}
        actions={
          <>
            <Button asChild variant="outline" size="sm" className="cursor-pointer">
              <Link to={`/teams/${teamCode}/security/scan-report`}>
                <ScanSearch className="h-4 w-4" /> Scan report
              </Link>
            </Button>
            <Button asChild size="sm" className="cursor-pointer">
              <Link to={`/teams/${teamCode}/security/remediation`}>
                <Wrench className="h-4 w-4" /> Remediation
              </Link>
            </Button>
          </>
        }
      />

      <QueryBoundary query={findingsQuery} variant="card" count={4} className="grid-cols-4">
        {(findings) => <DashboardBody findings={findings} teamCode={teamCode} />}
      </QueryBoundary>
    </div>
  )
}

function DashboardBody({ findings, teamCode }) {
  const stats = useMemo(() => {
    const open = findings.filter((f) => f.status !== 'closed')
    const critical = findings.filter((f) => f.priority === 'Critical')
    const avgRisk = Math.round(
      findings.reduce((sum, f) => sum + f.riskScore, 0) / (findings.length || 1),
    )
    const closed = findings.filter((f) => f.status === 'closed')
    return {
      openCount: open.length,
      criticalCount: critical.length,
      avgRisk,
      closedCount: closed.length,
      total: findings.length,
    }
  }, [findings])

  const categoryBreakdown = useMemo(() => {
    return CATEGORY_OPTIONS.map((option) => {
      const items = findings.filter((f) => f.category === option.value)
      return { ...option, count: items.length, open: items.filter((f) => f.status !== 'closed').length }
    })
  }, [findings])

  const recentFindings = useMemo(
    () => [...findings].sort((a, b) => b.riskScore - a.riskScore).slice(0, 4),
    [findings],
  )

  const maxCategoryCount = Math.max(1, ...categoryBreakdown.map((c) => c.count))

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={ShieldAlert}
          label="Open findings"
          value={stats.openCount}
          trend={`${stats.total} total findings tracked`}
          tone="danger"
        />
        <StatCard
          icon={Gauge}
          label="Critical severity"
          value={stats.criticalCount}
          trend="CVSS-scored, deterministically confirmed"
          tone="warning"
        />
        <StatCard
          icon={ShieldCheck}
          label="Avg. project-context risk"
          value={`${stats.avgRisk}/100`}
          trend="Severity + exposure + reachability"
          tone="primary"
        />
        <StatCard
          icon={GraduationCap}
          label="Tutor-verified closed"
          value={stats.closedCount}
          trend="Closed only after comprehension check"
          tone="success"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <Card className="lg:col-span-3 p-5 bg-card border-border shadow-xs space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-foreground">OWASP category breakdown</h3>
            <p className="text-[11px] text-muted-foreground">
              Findings per vulnerability category, detected deterministically before any LLM
              interpretation.
            </p>
          </div>
          <div className="space-y-3">
            {categoryBreakdown.map((category) => (
              <div key={category.value} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-foreground">{category.label}</span>
                  <span className="text-muted-foreground font-mono">
                    {category.count} finding{category.count === 1 ? '' : 's'}
                    {category.open > 0 && (
                      <span className="text-destructive ml-1.5">({category.open} open)</span>
                    )}
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-300"
                    style={{ width: `${(category.count / maxCategoryCount) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="lg:col-span-2 p-5 bg-card border-border shadow-xs space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Secure SDLC phase coverage</h3>
            <p className="text-[11px] text-muted-foreground">
              Design is merged into Requirements — same evidence stage, no separate artefact type.
            </p>
          </div>
          <ul className="space-y-3">
            {SDLC_PHASES.map((item) => (
              <li key={item.phase} className="flex items-start gap-2.5">
                <span
                  className={`mt-0.5 h-2 w-2 rounded-full shrink-0 ${item.covered ? 'bg-emerald-500' : 'bg-muted-foreground/40'}`}
                />
                <div>
                  <p className="text-xs font-semibold text-foreground">{item.phase}</p>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">{item.detail}</p>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card className="p-5 bg-card border-border shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Highest-risk findings</h3>
            <p className="text-[11px] text-muted-foreground">
              Ranked by project-context risk score, not severity alone.
            </p>
          </div>
          <Button asChild variant="ghost" size="sm" className="text-xs cursor-pointer">
            <Link to={`/teams/${teamCode}/security/scan-report`}>
              View all <ChevronRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        </div>
        <div className="space-y-2">
          {recentFindings.map((finding) => (
            <div
              key={finding.id}
              className="flex items-center justify-between gap-3 rounded-lg border border-border/70 p-3 hover:border-primary/40 transition-colors"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground truncate">{finding.title}</p>
                <p className="text-[11px] text-muted-foreground font-mono truncate">
                  {finding.file}
                  {finding.line ? `:${finding.line}` : ''}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Badge variant="outline" className="font-mono text-[10px]">
                  Risk {finding.riskScore}
                </Badge>
                <PriorityBadge priority={finding.priority} />
                <StatusBadge status={finding.status} />
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-5 bg-card border-border shadow-xs">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-primary/10 text-primary shrink-0">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div className="text-xs text-muted-foreground leading-relaxed">
            <span className="font-semibold text-foreground">Governance:</span> every finding shown
            here was confirmed by a deterministic scanner before any LLM interpreted it. Findings
            are learning signals for this student only — they are never used as grade inputs.
          </div>
        </div>
      </Card>
    </div>
  )
}

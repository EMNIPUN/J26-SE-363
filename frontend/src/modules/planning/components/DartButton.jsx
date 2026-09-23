import { useState } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { Gavel, ChevronDown, AlertTriangle, GitBranch, CheckCircle2 } from 'lucide-react'
import Badge from '../../../shared/components/Badge.jsx'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import AgentBadge from './AgentBadge.jsx'
import { usePlanningData } from '../context/usePlanningData.js'
import { ARBITRATION_CASES, TEAM_MEMBERS, GROUPS } from '../data/mockData.js'
import { ARBITRATION_CATEGORY_TONE } from '../utils.js'

const CONTEXT_LABEL = {
  dashboard: 'Project Overview',
  quality: 'SRS Quality',
  decomposition: 'Decomposition',
  effort: 'Effort Estimation',
  sprint: 'Sprint Management',
  cohort: 'Cohort Overview',
}

function groupForRequirement(reqId) {
  return GROUPS.find((g) => g.requirementIds.includes(reqId))
}

function isEscalated(c) {
  return c.category === 'NOVEL' || c.confidenceAgreement < 40
}

function ArbitrationCaseItem({ item }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between gap-2 p-3 text-left cursor-pointer hover:bg-muted/40 transition-colors"
      >
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 mb-1 flex-wrap">
            <Badge tone={ARBITRATION_CATEGORY_TONE[item.category]}>{item.category}</Badge>
            <span className="text-xs text-muted-foreground">{item.requirementId}</span>
          </div>
          <p className="text-xs font-medium text-foreground leading-snug">{item.title}</p>
        </div>
        <ChevronDown className={`h-3.5 w-3.5 text-muted-foreground shrink-0 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>
      {expanded && (
        <div className="px-3 pb-3 space-y-2 animate-fade-rise">
          {Object.entries(item.agentRationale).map(([agentKey, r]) => (
            <div key={agentKey} className="p-2 rounded-md bg-muted/30">
              <div className="flex items-center justify-between mb-1">
                <AgentBadge agent={agentKey} />
                <span className="text-[10px] text-muted-foreground">{r.confidence}% conf.</span>
              </div>
              <p className="text-xs text-foreground">{r.verdict}</p>
              <p className="text-[11px] text-muted-foreground leading-snug mt-0.5">{r.rationale}</p>
            </div>
          ))}
          <div className="p-2 rounded-md border border-primary/20 bg-primary/5">
            <p className="text-xs text-foreground leading-snug">{item.resolution}</p>
          </div>
        </div>
      )}
    </div>
  )
}

function buildEffortInsights(requirements, userStories, estimations) {
  const insights = []
  for (const req of requirements) {
    for (const story of userStories[req.id] || []) {
      const est = estimations[story.id]
      if (!est) continue
      const compareTo = est.finalPoints ?? est.studentPoints
      if (compareTo != null && Math.abs(compareTo - est.aiPoints) >= 2) {
        insights.push({ story, req, est, diff: compareTo - est.aiPoints })
      }
    }
  }
  return insights
}

function buildSprintInsights(kanbanTasks) {
  const blocked = kanbanTasks.filter((t) => t.status === 'Blocked')
  const workload = TEAM_MEMBERS.map((m) => {
    const assigned = kanbanTasks.filter((t) => t.assigneeId === m.id && t.status !== 'Done')
    const current = assigned.reduce((s, t) => s + t.points, 0)
    return { member: m, current, over: current > m.capacity }
  }).filter((w) => w.over)
  return { blocked, workload }
}

export default function DartButton({ context = 'dashboard' }) {
  const [open, setOpen] = useState(false)
  const { requirements, userStories, estimations, kanbanTasks } = usePlanningData()

  const qualityCases = ARBITRATION_CASES.filter((c) => c.stage === 'quality')
  const decompositionCases = ARBITRATION_CASES.filter((c) => c.stage === 'decomposition')
  const effortInsights = buildEffortInsights(requirements, userStories, estimations)
  const sprintInsights = buildSprintInsights(kanbanTasks)
  const openCount = ARBITRATION_CASES.filter((c) => c.status === 'Open').length

  const escalatedCases = ARBITRATION_CASES.filter((c) => c.status === 'Open' && isEscalated(c))
  const categoryTally = ARBITRATION_CASES.reduce((acc, c) => {
    acc[c.category] = (acc[c.category] || 0) + 1
    return acc
  }, {})

  const badgeCount =
    context === 'quality'
      ? qualityCases.filter((c) => c.status === 'Open').length
      : context === 'decomposition'
        ? decompositionCases.filter((c) => c.status === 'Open').length
        : context === 'effort'
          ? effortInsights.length
          : context === 'sprint'
            ? sprintInsights.blocked.length + sprintInsights.workload.length
            : context === 'cohort'
              ? escalatedCases.length
              : openCount + effortInsights.length + sprintInsights.blocked.length + sprintInsights.workload.length

  return (
    <>
      {createPortal(
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="fixed bottom-6 left-6 z-40 flex items-center gap-2 px-4 py-2.5 rounded-full bg-foreground text-background shadow-lg hover:shadow-xl hover:scale-105 active:scale-95 transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] cursor-pointer group"
        >
          <Gavel className="h-4 w-4 shrink-0" />
          <span className="text-xs font-semibold tracking-tight">DART</span>
          {badgeCount > 0 && (
            <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-destructive-foreground px-1">
              {badgeCount}
            </span>
          )}
        </button>,
        document.body,
      )}

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto column-scroll-contain">
          <SheetHeader>
            <div className="flex items-center gap-2">
              <Gavel className="h-4 w-4 text-primary" />
              <SheetTitle>DART</SheetTitle>
            </div>
            <SheetDescription>
              Diagnostic Arbitration via Reasoning Traces · Current context: <strong>{CONTEXT_LABEL[context]}</strong>
            </SheetDescription>
          </SheetHeader>

          <div className="px-4 pb-4 space-y-5">
            {context === 'quality' && (
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Requirement-level conflicts
                </p>
                {qualityCases.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No quality disagreements detected right now.</p>
                ) : (
                  qualityCases.map((c) => <ArbitrationCaseItem key={c.id} item={c} />)
                )}
              </div>
            )}

            {context === 'decomposition' && (
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Decomposition conflicts
                </p>
                {decompositionCases.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No decomposition disagreements detected right now.</p>
                ) : (
                  decompositionCases.map((c) => <ArbitrationCaseItem key={c.id} item={c} />)
                )}
              </div>
            )}

            {context === 'effort' && (
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Estimate disagreements
                </p>
                {effortInsights.length === 0 ? (
                  <p className="text-xs text-muted-foreground">Your estimates and the AI's are closely aligned.</p>
                ) : (
                  effortInsights.map(({ story, req, est, diff }) => (
                    <div key={story.id} className="p-3 rounded-lg border border-border">
                      <p className="text-xs font-medium text-foreground mb-1">{story.title}</p>
                      <p className="text-[11px] text-muted-foreground mb-1.5">
                        {req.id} · You: {est.finalPoints ?? est.studentPoints ?? '—'} SP · AI: {est.aiPoints} SP ·{' '}
                        <span className={diff > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-primary'}>
                          {diff > 0 ? `+${diff}` : diff} SP
                        </span>
                      </p>
                      <ul className="text-[11px] text-muted-foreground list-disc list-inside space-y-0.5">
                        {est.aiFactors?.map((f) => (
                          <li key={f}>{f}</li>
                        ))}
                      </ul>
                    </div>
                  ))
                )}
              </div>
            )}

            {context === 'sprint' && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Blocked tasks</p>
                  {sprintInsights.blocked.length === 0 ? (
                    <p className="text-xs text-muted-foreground">Nothing is blocked right now.</p>
                  ) : (
                    sprintInsights.blocked.map((t) => (
                      <div key={t.id} className="p-3 rounded-lg border border-destructive/20 bg-destructive/5">
                        <p className="text-xs font-medium text-foreground mb-1">
                          {t.id} — {t.title}
                        </p>
                        <p className="text-[11px] text-muted-foreground">
                          <span className="font-semibold text-destructive">Dependency</span> — {t.blockedReason}
                        </p>
                      </div>
                    ))
                  )}
                </div>
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Workload balance</p>
                  {sprintInsights.workload.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No one is over capacity this sprint.</p>
                  ) : (
                    sprintInsights.workload.map((w) => (
                      <div key={w.member.id} className="p-3 rounded-lg border border-amber-500/20 bg-amber-500/5">
                        <p className="text-xs font-medium text-foreground">
                          {w.member.name} — {w.current}/{w.member.capacity} SP
                        </p>
                        <p className="text-[11px] text-muted-foreground mt-0.5">
                          Potential cause: uneven task allocation this sprint.
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {context === 'cohort' && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Escalated to instructor ({escalatedCases.length})
                  </p>
                  {escalatedCases.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No cases need lecturer review right now.</p>
                  ) : (
                    escalatedCases.map((c) => {
                      const group = groupForRequirement(c.requirementId)
                      return (
                        <div key={c.id} className="p-3 rounded-lg border border-destructive/20 bg-destructive/5">
                          <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                            <Badge tone={ARBITRATION_CATEGORY_TONE[c.category]}>{c.category}</Badge>
                            {group && <span className="text-xs text-muted-foreground">{group.name}</span>}
                            <span className="text-[10px] text-muted-foreground ml-auto">{c.confidenceAgreement}% agreement</span>
                          </div>
                          <p className="text-xs font-medium text-foreground">{c.title}</p>
                        </div>
                      )
                    })
                  )}
                </div>
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">DART category distribution</p>
                  <ul className="space-y-1">
                    {Object.entries(categoryTally).map(([cat, count]) => (
                      <li key={cat} className="flex items-center justify-between text-xs">
                        <Badge tone={ARBITRATION_CATEGORY_TONE[cat]}>{cat}</Badge>
                        <span className="text-foreground font-medium">{count}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <Link to="/planning/instructor/arbitration" className="text-xs text-primary hover:underline inline-block">
                  Open Arbitration Oversight
                </Link>
              </div>
            )}

            {context === 'dashboard' && (
              <div className="space-y-2.5">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Project insights</p>
                <div className="flex items-start gap-2 text-xs">
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />
                  <span className="text-foreground">
                    {qualityCases.filter((c) => c.status === 'Open').length} requirement(s) have unresolved quality conflicts.
                  </span>
                </div>
                <div className="flex items-start gap-2 text-xs">
                  <GitBranch className="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />
                  <span className="text-foreground">
                    {decompositionCases.filter((c) => c.status === 'Open').length} decomposition conflict(s) detected.
                  </span>
                </div>
                <div className="flex items-start gap-2 text-xs">
                  <AlertTriangle className="h-3.5 w-3.5 text-primary mt-0.5 shrink-0" />
                  <span className="text-foreground">
                    AI and student effort estimates differ significantly for {effortInsights.length} stor{effortInsights.length === 1 ? 'y' : 'ies'}.
                  </span>
                </div>
                <div className="flex items-start gap-2 text-xs">
                  <AlertTriangle className="h-3.5 w-3.5 text-destructive mt-0.5 shrink-0" />
                  <span className="text-foreground">
                    {sprintInsights.blocked.length} sprint task(s) blocked, {sprintInsights.workload.length} member(s) over capacity.
                  </span>
                </div>
                {openCount === 0 && effortInsights.length === 0 && sprintInsights.blocked.length === 0 && (
                  <div className="flex items-start gap-2 text-xs">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 mt-0.5 shrink-0" />
                    <span className="text-foreground">No unresolved critical conflicts.</span>
                  </div>
                )}
                <div className="pt-2 flex flex-wrap gap-3">
                  <Link to="/planning/requirements/srs-quality" className="text-xs text-primary hover:underline">
                    Review SRS Quality
                  </Link>
                  <Link to="/planning/sprint-management" className="text-xs text-primary hover:underline">
                    Review Sprint Board
                  </Link>
                </div>
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}

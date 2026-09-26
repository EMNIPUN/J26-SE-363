import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  Wrench,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Loader2,
  GraduationCap,
  RotateCcw,
  Sparkles,
} from 'lucide-react'
import PageHeader from '@/shared/components/PageHeader.jsx'
import QueryBoundary from '@/shared/components/QueryBoundary.jsx'
import EmptyState from '@/shared/components/EmptyState.jsx'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useScope } from '@/shared/context/useScope.js'
import { showToast } from '@/shared/utils/toast.jsx'
import { useSecurityFindings } from '../hooks/useSecurityFindings.js'
import { PriorityBadge, StatusBadge } from '../components/FindingBadges.jsx'
import CodeBlock from '../components/CodeBlock.jsx'

export default function RemediationDetail() {
  const findingsQuery = useSecurityFindings()

  return (
    <QueryBoundary query={findingsQuery} variant="card" count={2}>
      {(findings) => <RemediationDetailBody allFindings={findings} />}
    </QueryBoundary>
  )
}

function RemediationDetailBody({ allFindings }) {
  const { teamId, findingId } = useParams()
  const { selectedGroup } = useScope()
  const navigate = useNavigate()
  const teamCode = selectedGroup?.code || teamId || 'J26-SE-363'
  const remediationHref = `/teams/${teamCode}/security/remediation`

  const original = allFindings.find((f) => f.id === findingId) || null

  if (!original) {
    return (
      <div className="space-y-6 animate-fade-rise">
        <PageHeader
          title="Remediation"
          breadcrumb={['Project Security', 'Remediation']}
          description="This finding could not be found."
        />
        <EmptyState
          title="Finding not found"
          description="It may have already been closed, or the link is out of date."
          actionLabel="Back to remediation list"
          onAction={() => navigate(remediationHref)}
        />
      </div>
    )
  }

  // Keying by finding id remounts the workspace (and resets its local state)
  // whenever the student navigates between two different findings.
  return (
    <RemediationWorkspace key={original.id} initialFinding={original} remediationHref={remediationHref} />
  )
}

function RemediationWorkspace({ initialFinding, remediationHref }) {
  const [finding, setFinding] = useState(initialFinding)
  const [checkStage, setCheckStage] = useState('idle') // idle | connecting | connected

  useEffect(() => {
    if (checkStage !== 'connecting') return undefined
    const timer = setTimeout(() => setCheckStage('connected'), 900)
    return () => clearTimeout(timer)
  }, [checkStage])

  const startLearningCheck = () => setCheckStage('connecting')

  const markFixed = () => {
    setFinding((prev) => ({ ...prev, status: 'learning' }))
    showToast.info('Fix applied (prototype)', {
      description: 'Start the learning check to verify understanding before this can close.',
    })
  }

  const resolveCheck = (outcome) => {
    if (outcome === 'passed') {
      setFinding((prev) => ({
        ...prev,
        status: 'closed',
        verification: {
          taught: prev.explanation,
          checkResult: 'Passed (comprehension threshold met)',
          outcome: 'Student explained the root cause and why the fix is safe.',
        },
      }))
      showToast.success('Finding closed', {
        description: 'Tutor Agent confirmed comprehension. Finding marked as closed.',
      })
      setCheckStage('idle')
    } else {
      setFinding((prev) => ({ ...prev, status: 'learning' }))
      showToast.info('Retry needed', {
        description: 'Comprehension threshold not met yet — status set to awaiting learning check.',
      })
      setCheckStage('idle')
    }
  }

  return (
    <div className="space-y-6 animate-fade-rise">
      <PageHeader
        title={finding.title}
        breadcrumb={['Project Security', 'Remediation', finding.title]}
        description="Evidence-grounded fix guidance, closed only once a Tutor-verified learning check confirms understanding."
        actions={
          <Button asChild variant="outline" size="sm" className="cursor-pointer">
            <Link to={remediationHref}>
              <ArrowLeft className="h-4 w-4" /> Back to remediation list
            </Link>
          </Button>
        }
      />

      <div className="space-y-4">
        <Card className="p-5 bg-card border-border shadow-xs space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <PriorityBadge priority={finding.priority} />
            <StatusBadge status={finding.status} />
            <span className="text-[11px] text-muted-foreground font-mono">{finding.cwe}</span>
          </div>
          <div>
            <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
              <Wrench className="h-4 w-4 text-primary" /> {finding.title}
            </h2>
            <p className="text-[11px] text-muted-foreground font-mono mt-0.5">
              {finding.file}
              {finding.line ? `:${finding.line}` : ''}
              {finding.endpoint ? ` • ${finding.endpoint}` : ''}
            </p>
          </div>
          <p className="text-sm text-foreground leading-relaxed">{finding.explanation}</p>
          <p className="text-xs text-muted-foreground leading-relaxed">{finding.whyItMatters}</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-destructive">
                Before (vulnerable)
              </h4>
              <CodeBlock lines={finding.before.split('\n')} className="bg-destructive/5 border-destructive/20" />
            </div>
            <div className="space-y-1.5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                After (secure fix)
              </h4>
              <CodeBlock lines={finding.after.split('\n')} className="bg-emerald-500/5 border-emerald-500/20" />
            </div>
          </div>

          {finding.status === 'closed' && finding.verification ? (
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
              <div className="text-xs">
                <p className="font-semibold text-foreground">Tutor-verified and closed</p>
                <p className="text-muted-foreground mt-0.5">{finding.verification.outcome}</p>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <Button
                size="sm"
                variant="outline"
                className="cursor-pointer"
                onClick={markFixed}
                disabled={finding.status === 'learning'}
              >
                {finding.status === 'learning' ? 'Fix applied' : 'Mark fix applied'}
              </Button>
              <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
              <Button
                size="sm"
                className="cursor-pointer"
                onClick={startLearningCheck}
                disabled={checkStage !== 'idle'}
              >
                <GraduationCap className="h-4 w-4" /> Start learning check
              </Button>
            </div>
          )}
        </Card>

        {checkStage !== 'idle' && (
          <LearningCheckCard
            finding={finding}
            stage={checkStage}
            onResolve={resolveCheck}
            onCancel={() => setCheckStage('idle')}
          />
        )}
      </div>
    </div>
  )
}

function LearningCheckCard({ finding, stage, onResolve, onCancel }) {
  return (
    <Card className="p-5 bg-card border-primary/20 shadow-xs space-y-4">
      <div className="flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold text-foreground">Adaptive AI Tutor Agent</h3>
      </div>

      {stage === 'connecting' && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground py-6 justify-center">
          <Loader2 className="h-4 w-4 animate-spin" /> Connecting to the Tutor Agent (Channel B)…
        </div>
      )}

      {stage === 'connected' && (
        <div className="space-y-4">
          <div className="rounded-lg border border-border bg-muted/30 p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">
              Probe question
            </p>
            <p className="text-sm text-foreground">{finding.probeQuestion}</p>
          </div>
          <p className="text-xs text-muted-foreground">
            This is a prototype handoff placeholder — the real conversation and scoring are
            owned by the Tutor Agent, not this subsystem. Use the buttons below to simulate its
            two possible outcomes.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" className="cursor-pointer" onClick={() => onResolve('passed')}>
              <CheckCircle2 className="h-4 w-4" /> Simulate: comprehension passed
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="cursor-pointer"
              onClick={() => onResolve('retry')}
            >
              <RotateCcw className="h-4 w-4" /> Simulate: retry needed
            </Button>
            <Button size="sm" variant="ghost" className="cursor-pointer" onClick={onCancel}>
              Return to finding
            </Button>
          </div>
        </div>
      )}
    </Card>
  )
}

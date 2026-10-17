import { useState } from 'react'
import { ChevronDown, Lightbulb, AlertTriangle, CheckCircle2 } from 'lucide-react'
import Card from '../../../shared/components/Card.jsx'
import Badge from '../../../shared/components/Badge.jsx'
import EmptyState from '../../../shared/components/EmptyState.jsx'
import FeedbackList from './FeedbackList.jsx'

const READINESS_COPY = {
  Ready: {
    tone: 'success',
    label: 'Ready for effort estimation',
  },
  'Ready with Improvements': {
    tone: 'warning',
    label: 'Ready, with a few suggested improvements',
  },
  'Needs Attention': {
    tone: 'primary',
    label: 'Needs attention — but you can still proceed provisionally',
  },
}

function ReadinessBanner({ evaluation }) {
  const copy = READINESS_COPY[evaluation.readiness] || READINESS_COPY['Needs Attention']
  return (
    <div
      className={`p-3.5 rounded-xl border flex items-center gap-2.5 ${
        copy.tone === 'success'
          ? 'border-emerald-500/30 bg-emerald-500/5'
          : copy.tone === 'primary'
            ? 'border-blue-500/30 bg-blue-500/5'
            : 'border-amber-500/30 bg-amber-500/5'
      }`}
    >
      {copy.tone === 'success' ? (
        <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
      ) : (
        <AlertTriangle
          className={`h-4 w-4 shrink-0 ${
            copy.tone === 'primary' ? 'text-blue-600 dark:text-blue-400' : 'text-amber-600 dark:text-amber-400'
          }`}
        />
      )}
      <div className="min-w-0">
        <p
          className={`text-xs font-bold ${
            copy.tone === 'success'
              ? 'text-emerald-700 dark:text-emerald-400'
              : copy.tone === 'primary'
                ? 'text-blue-700 dark:text-blue-400'
                : 'text-amber-800 dark:text-amber-300'
          }`}
        >
          {evaluation.readiness} — {copy.label}
        </p>
        {evaluation.readinessReason && (
          <p className="text-[11px] text-muted-foreground mt-0.5">{evaluation.readinessReason}</p>
        )}
      </div>
    </div>
  )
}

export default function DecompositionEvidencePanel({ evaluation }) {
  const [open, setOpen] = useState(true)

  if (!evaluation) {
    return (
      <Card className="p-6 text-center">
        <EmptyState
          icon={Lightbulb}
          title="No agent evidence yet"
          description="Run a decomposition analysis to see the agent's readiness assessment and feedback here."
        />
      </Card>
    )
  }

  if (evaluation.analysisFailed) {
    return (
      <Card className="p-4 border-destructive/30 bg-destructive/5">
        <div className="flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
          <div>
            <p className="text-xs text-destructive font-semibold">
              Analysis could not be completed — this is not a real result
            </p>
            <p className="text-[11px] text-destructive/90 mt-0.5">
              A system error prevented the agent from evaluating coverage
              {evaluation.failureReason ? ` (${evaluation.failureReason})` : ''}. Re-run analysis once the issue is
              resolved — the score and checklist shown elsewhere on this page are placeholders, not findings.
            </p>
          </div>
        </div>
      </Card>
    )
  }

  if (evaluation.malformed) {
    return (
      <Card className="p-4 border-destructive/30 bg-destructive/5">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
          <p className="text-xs text-destructive font-semibold">
            {evaluation.persistError || 'Analysis response was malformed or incomplete.'}
          </p>
        </div>
      </Card>
    )
  }

  const { studentFeedback, score, qualityBand } = evaluation

  return (
    <Card className="p-0 overflow-hidden border-border bg-card">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-muted/40 transition-colors cursor-pointer"
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Lightbulb className="h-4 w-4 text-primary" />
          Agent Reasoning Evidence &amp; Feedback
        </span>
        <div className="flex items-center gap-2">
          <Badge
            tone={
              evaluation.readiness === 'Ready'
                ? 'success'
                : evaluation.readiness === 'Needs Attention'
                  ? 'warning'
                  : 'primary'
            }
            className="text-[10px] px-2 py-0.5"
          >
            {evaluation.readiness}
          </Badge>
          <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${open ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-4 border-t border-border/60 pt-4">
          {evaluation.stale && (
            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/25 text-amber-800 dark:text-amber-300">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
              <p className="text-[11px]">Stories changed since this analysis — showing the last result.</p>
            </div>
          )}

          <ReadinessBanner evaluation={evaluation} />

          {/* Actionable feedback checklist — the agent's primary output, most important first */}
          <FeedbackList bullets={studentFeedback} heading="Top Improvements" />

          {/* Score + band — secondary context only, never the primary verdict */}
          <div className="flex items-center gap-2 pt-1 border-t border-border/40">
            <span className="text-[11px] text-muted-foreground">Decomposition quality:</span>
            <Badge tone="neutral" className="text-[10px] px-2 py-0.5">
              {score}/4 · {qualityBand}
            </Badge>
          </div>
        </div>
      )}
    </Card>
  )
}

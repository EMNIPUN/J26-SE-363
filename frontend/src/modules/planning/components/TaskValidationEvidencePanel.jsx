import { AlertTriangle, CheckCircle2 } from 'lucide-react'
import Badge from '../../../shared/components/Badge.jsx'
import FeedbackList from './FeedbackList.jsx'

const READINESS_COPY = {
  Valid: { tone: 'success', label: 'Ready for effort estimation' },
  'Needs Improvement': { tone: 'warning', label: 'Ready, with a few suggested improvements' },
  'Coverage Warning': { tone: 'primary', label: 'Missing work — but you can still proceed provisionally' },
}

/**
 * Compact, inline task-validation evidence block nested inside a story's
 * task section — mirrors DecompositionEvidencePanel's readiness banner +
 * feedback pattern, but without its own collapsible header since it already
 * lives inside the story card's existing structure.
 */
export default function TaskValidationEvidencePanel({ evaluation }) {
  if (!evaluation) return null

  if (evaluation.analysisFailed) {
    return (
      <div className="mt-3 p-3 rounded-lg border border-destructive/30 bg-destructive/5">
        <div className="flex items-start gap-2">
          <AlertTriangle className="h-3.5 w-3.5 text-destructive shrink-0 mt-0.5" />
          <div>
            <p className="text-xs text-destructive font-semibold">
              Task validation could not be completed — this is not a real result
            </p>
            <p className="text-[11px] text-destructive/90 mt-0.5">
              A system error prevented the agent from evaluating your tasks
              {evaluation.failureReason ? ` (${evaluation.failureReason})` : ''}. Re-run validation once the issue
              is resolved.
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (evaluation.malformed) {
    return (
      <div className="mt-3 p-3 rounded-lg border border-destructive/30 bg-destructive/5 flex items-center gap-2">
        <AlertTriangle className="h-3.5 w-3.5 text-destructive shrink-0" />
        <p className="text-xs text-destructive font-semibold">
          {evaluation.persistError || 'Validation response was malformed or incomplete.'}
        </p>
      </div>
    )
  }

  const copy = READINESS_COPY[evaluation.readiness] || READINESS_COPY['Coverage Warning']

  return (
    <div className="space-y-3 mt-3 pt-3 border-t border-border/60">
      {evaluation.stale && (
        <div className="flex items-center gap-2 p-2 rounded-lg bg-amber-500/10 border border-amber-500/25 text-amber-800 dark:text-amber-300">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          <p className="text-[11px]">Tasks changed since this validation — showing the last result.</p>
        </div>
      )}

      <div
        className={`p-2.5 rounded-lg border flex items-center gap-2 ${
          copy.tone === 'success'
            ? 'border-emerald-500/30 bg-emerald-500/5'
            : copy.tone === 'primary'
              ? 'border-blue-500/30 bg-blue-500/5'
              : 'border-amber-500/30 bg-amber-500/5'
        }`}
      >
        {copy.tone === 'success' ? (
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
        ) : (
          <AlertTriangle
            className={`h-3.5 w-3.5 shrink-0 ${
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

      <FeedbackList bullets={evaluation.studentFeedback} heading="Top Improvements" />

      <div className="flex items-center gap-2">
        <span className="text-[11px] text-muted-foreground">Task breakdown quality:</span>
        <Badge tone="neutral" className="text-[10px] px-2 py-0.5">
          {evaluation.score}/4 · {evaluation.qualityBand}
        </Badge>
      </div>
    </div>
  )
}

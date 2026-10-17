import { useState } from 'react'
import { Circle, Info } from 'lucide-react'

const TOP_FEEDBACK_COUNT = 3

/** Splits a "<finding> → <suggestion>" feedback bullet into its two parts, if present. */
function splitBullet(bullet) {
  const idx = bullet.indexOf(' → ')
  if (idx === -1) return { finding: bullet, suggestion: '' }
  return { finding: bullet.slice(0, idx), suggestion: bullet.slice(idx + 3) }
}

function FeedbackItem({ bullet, emphasized }) {
  const { finding, suggestion } = splitBullet(bullet)
  return (
    <li
      className={`flex items-start gap-2 text-xs rounded-lg ${
        emphasized ? 'p-2.5 bg-muted/40 border border-border/60' : ''
      }`}
    >
      <Circle className={`h-2.5 w-2.5 mt-1 shrink-0 fill-current ${emphasized ? 'text-primary' : 'text-muted-foreground'}`} />
      <div className="min-w-0">
        <span className="text-foreground">{finding}</span>
        {suggestion && (
          <div className="flex items-start gap-1.5 mt-1 text-[11px] text-muted-foreground">
            <Info className="h-3 w-3 mt-0.5 text-primary shrink-0" />
            <span>
              <span className="font-semibold text-foreground/80">Try: </span>
              {suggestion}
            </span>
          </div>
        )}
      </div>
    </li>
  )
}

/**
 * Shared agent-feedback checklist: the top 3 bullets shown prominently, the
 * rest behind a "show more" toggle. Used by both the decomposition and task
 * validation evidence panels so the two features present feedback the same
 * way. `bullets` is a flat list of strings, each optionally formatted as
 * "<finding> → <suggestion>" (the agents' scorer modules emit this shape).
 */
export default function FeedbackList({ bullets, emptyLabel = 'No feedback returned by the agent.', heading }) {
  const [showAll, setShowAll] = useState(false)
  const feedback = bullets || []
  const top = feedback.slice(0, TOP_FEEDBACK_COUNT)
  const rest = feedback.slice(TOP_FEEDBACK_COUNT)

  return (
    <section>
      {heading && (
        <h4 className="text-xs font-bold uppercase tracking-wide text-muted-foreground mb-2">
          {feedback.length > 0 ? heading : 'Feedback'}
        </h4>
      )}
      {feedback.length > 0 ? (
        <>
          <ul className="space-y-2">
            {top.map((bullet, i) => (
              <FeedbackItem key={i} bullet={bullet} emphasized />
            ))}
          </ul>
          {rest.length > 0 && (
            <div className="mt-2">
              <button
                type="button"
                onClick={() => setShowAll((v) => !v)}
                className="text-[11px] font-semibold text-primary hover:underline cursor-pointer"
              >
                {showAll ? 'Show fewer' : `Show ${rest.length} more improvement${rest.length > 1 ? 's' : ''}`}
              </button>
              {showAll && (
                <ul className="space-y-1.5 mt-2">
                  {rest.map((bullet, i) => (
                    <FeedbackItem key={i} bullet={bullet} />
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      ) : (
        <p className="text-xs text-muted-foreground italic">{emptyLabel}</p>
      )}
    </section>
  )
}

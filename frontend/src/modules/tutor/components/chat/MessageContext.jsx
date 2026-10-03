import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { getActionPath, useTutorPaths } from '../../utils/tutorPaths.js'

function ContextItem({ label, children }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] text-muted-foreground">{label}</dt>
      <dd className="text-xs font-semibold text-foreground">{children}</dd>
    </div>
  )
}

// The learning context the Tutor attaches to a reply.
export default function MessageContext({ context, action }) {
  const paths = useTutorPaths()
  const actionPath = getActionPath(paths, action)
  if (!context && !actionPath) return null

  return (
    <div className="mt-2 rounded-lg border border-border/60 bg-card px-3 py-2.5">
      {context && (
        <dl className="flex flex-wrap gap-x-6 gap-y-2">
          {context.conceptLabel && <ContextItem label="Related concept">{context.conceptLabel}</ContextItem>}
          {context.competency != null && (
            <ContextItem label="Current competency">
              <span className="tabular-nums">{context.competency}%</span>
            </ContextItem>
          )}
          {context.recommendedAction && <ContextItem label="Recommended">{context.recommendedAction}</ContextItem>}
        </dl>
      )}
      {actionPath && (
        <Button asChild size="sm" variant="outline" className={cn(context && 'mt-2.5')}>
          <Link to={actionPath}>
            {action.label}
            <ArrowRight aria-hidden="true" />
          </Link>
        </Button>
      )}
    </div>
  )
}

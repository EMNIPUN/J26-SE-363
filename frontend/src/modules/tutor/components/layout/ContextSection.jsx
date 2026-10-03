import { useId } from 'react'
import { cn } from '@/lib/utils'

export default function ContextSection({ icon: Icon, title, description, action, className, children }) {
  const headingId = useId()

  return (
    <section
      aria-labelledby={headingId}
      className={cn('rounded-xl border border-border/60 bg-card p-4 text-card-foreground card-elevated', className)}
    >
      <header className="mb-3 flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2.5">
          {Icon && (
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Icon className="h-4 w-4" aria-hidden="true" />
            </span>
          )}
          <div className="min-w-0">
            <h2 id={headingId} className="text-sm font-semibold leading-7 text-foreground">
              {title}
            </h2>
            {description && <p className="text-xs leading-relaxed text-muted-foreground">{description}</p>}
          </div>
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </header>
      {children}
    </section>
  )
}

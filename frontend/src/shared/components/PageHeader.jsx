import { Fragment } from 'react'
import { ChevronRight } from 'lucide-react'

export default function PageHeader({ title, description, breadcrumb = [], actions }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 pb-6 mb-6 border-b border-border">
      <div className="min-w-0">
        {breadcrumb.length > 0 && (
          <nav aria-label="Breadcrumb" className="mb-2">
            <ol className="flex flex-wrap items-center gap-1 text-xs font-medium text-muted-foreground">
              {breadcrumb.map((crumb, idx) => {
                const isLast = idx === breadcrumb.length - 1
                return (
                  <Fragment key={`${crumb}-${idx}`}>
                    <li className={isLast ? 'text-foreground/80' : ''} aria-current={isLast ? 'page' : undefined}>
                      {crumb}
                    </li>
                    {!isLast && (
                      <li aria-hidden="true">
                        <ChevronRight className="h-3 w-3 opacity-60" />
                      </li>
                    )}
                  </Fragment>
                )
              })}
            </ol>
          </nav>
        )}
        <h1 className="text-2xl font-bold tracking-tight text-foreground">{title}</h1>
        {description && (
          <p className="text-sm text-muted-foreground mt-1.5 max-w-3xl leading-relaxed">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2 flex-wrap shrink-0">{actions}</div>}
    </div>
  )
}

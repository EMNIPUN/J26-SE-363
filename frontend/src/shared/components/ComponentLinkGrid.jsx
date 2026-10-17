import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'

const GRID_BY_COUNT = {
  3: 'grid-cols-1 @2xl:grid-cols-3',
  4: 'grid-cols-1 @xl:grid-cols-2 @5xl:grid-cols-4',
}

export default function ComponentLinkGrid({ items }) {
  return (
    <div className={`grid gap-4 ${GRID_BY_COUNT[items.length] || GRID_BY_COUNT[4]}`}>
      {items.map((m) => {
        const Icon = m.icon
        return (
          <Link
            key={m.key}
            to={m.to}
            className="group flex flex-col justify-between rounded-xl border border-border/60 bg-card p-5 card-elevated card-hover-lift active:scale-[0.99] outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <div>
              <div className="flex items-start justify-between gap-3">
                {Icon && (
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" strokeWidth={2} />
                  </span>
                )}
                <ArrowUpRight className="h-4 w-4 text-muted-foreground transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:text-primary group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </div>
              <h3 className="mt-4 text-base font-semibold text-foreground group-hover:text-primary transition-colors duration-150">
                {m.label}
              </h3>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{m.tagline}</p>
            </div>
            {m.owner && (
              <p className="mt-4 pt-3 border-t border-border text-[11px] font-medium text-muted-foreground truncate">
                {m.owner}
              </p>
            )}
          </Link>
        )
      })}
    </div>
  )
}

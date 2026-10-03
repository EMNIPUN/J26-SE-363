import { useId } from 'react'

export default function PlanSection({ icon: Icon, title, description, items, emptyMessage, renderItem }) {
  const headingId = useId()

  return (
    <section aria-labelledby={headingId}>
      <header className="mb-3 flex items-start gap-2.5">
        {Icon && (
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon className="h-4 w-4" aria-hidden="true" />
          </span>
        )}
        <div className="min-w-0">
          <h3 id={headingId} className="text-sm font-semibold leading-7 text-foreground">
            {title}
            {items.length > 0 && (
              <span className="ml-1.5 text-xs font-normal tabular-nums text-muted-foreground">({items.length})</span>
            )}
          </h3>
          {description && <p className="text-xs leading-relaxed text-muted-foreground">{description}</p>}
        </div>
      </header>
      {items.length > 0 ? (
        <ul className="grid gap-3 @2xl:grid-cols-2 @6xl:grid-cols-3">
          {items.map((item) => (
            <li key={item.id}>{renderItem(item)}</li>
          ))}
        </ul>
      ) : (
        <p className="rounded-lg border border-dashed border-border px-3 py-4 text-center text-xs text-muted-foreground">
          {emptyMessage}
        </p>
      )}
    </section>
  )
}

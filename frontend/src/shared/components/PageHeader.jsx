export default function PageHeader({ title, description, breadcrumb = [], actions }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 mb-6 border-b border-border">
      <div>
        {breadcrumb.length > 0 && (
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
            {breadcrumb.join(' / ')}
          </p>
        )}
        <h1 className="text-2xl font-bold tracking-tight text-foreground">{title}</h1>
        {description && (
          <p className="text-sm text-muted-foreground mt-1">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-3 flex-wrap">{actions}</div>}
    </div>
  )
}


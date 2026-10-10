// `breadcrumb` is still accepted from older pages, but the trail now lives in
// the top bar (built from the nav tree), so it is not rendered twice.
// eslint-disable-next-line no-unused-vars
export default function PageHeader({ title, description, breadcrumb, actions }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 pb-6 mb-6 border-b border-border">
      <div className="min-w-0">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">{title}</h1>
        {description && (
          <p className="text-sm text-muted-foreground mt-1.5 max-w-3xl leading-relaxed">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2 flex-wrap shrink-0">{actions}</div>}
    </div>
  )
}

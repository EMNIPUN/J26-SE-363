const STATUS_CLASS = {
  Demonstrated:
    'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300',
  Developing:
    'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300',
  'Needs Attention':
    'border-amber-300 bg-amber-50 text-amber-950 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-200',
  'Insufficient Evidence': 'border-border bg-muted text-muted-foreground',
}

export function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${
        STATUS_CLASS[status] || STATUS_CLASS['Insufficient Evidence']
      }`}
    >
      {status}
    </span>
  )
}

function formatScore(value) {
  return typeof value === 'number' ? `${value}` : 'Not estimated'
}

export default function CompetencyIndicator({ estimate }) {
  if (!estimate) {
    return <p className="text-sm text-muted-foreground">No competency snapshot was returned for this concept.</p>
  }

  const known = typeof estimate.estimated === 'number' && typeof estimate.required === 'number'
  const width = known ? Math.max(0, Math.min(100, estimate.estimated)) : 0

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <StatusBadge status={estimate.status} />
        <span className="text-xs text-muted-foreground">{estimate.confidence}</span>
      </div>
      <dl className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg border border-border px-2 py-2">
          <dt className="text-[11px] text-muted-foreground">Required</dt>
          <dd className="font-mono text-sm font-semibold">{formatScore(estimate.required)}</dd>
        </div>
        <div className="rounded-lg border border-border px-2 py-2">
          <dt className="text-[11px] text-muted-foreground">Estimated</dt>
          <dd className="font-mono text-sm font-semibold">{formatScore(estimate.estimated)}</dd>
        </div>
        <div className="rounded-lg border border-border px-2 py-2">
          <dt className="text-[11px] text-muted-foreground">Gap</dt>
          <dd className="font-mono text-sm font-semibold">
            {typeof estimate.gap === 'number' ? estimate.gap : '—'}
          </dd>
        </div>
      </dl>
      {known ? (
        <div className="h-1.5 overflow-hidden rounded-full bg-muted" aria-hidden="true">
          <div className="h-full rounded-full bg-primary" style={{ width: `${width}%` }} />
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          Missing evidence stays blank. It is not shown as zero competency.
        </p>
      )}
      <div>
        <p className="text-xs font-medium text-foreground">Evidence</p>
        {estimate.evidence?.length ? (
          <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
            {estimate.evidence.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-xs text-muted-foreground">No evidence is stored for this estimate.</p>
        )}
      </div>
    </div>
  )
}

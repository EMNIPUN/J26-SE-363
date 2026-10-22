function masteryLabel(probability) {
  if (probability == null) return 'Unknown (no usable evidence)'
  if (probability >= 0.75) return 'Strong mastery signal'
  if (probability >= 0.5) return 'Developing mastery'
  return 'Low mastery signal'
}

function formatPct(probability) {
  if (probability == null) return '—'
  return `${Math.round(probability * 100)}%`
}

export default function BktMasteryCard({ estimate }) {
  if (!estimate) return null

  const probability = estimate.mastery_probability
  const known = typeof probability === 'number'
  const width = known ? Math.max(0, Math.min(100, Math.round(probability * 100))) : 0

  return (
    <article className="rounded-xl border border-border bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            {estimate.concept_name || estimate.concept_id}
          </h3>
          <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">{estimate.concept_id}</p>
        </div>
        <span className="rounded-full border border-border px-2 py-0.5 text-xs font-medium">
          {estimate.model || 'BKT'}
        </span>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-2 text-center sm:grid-cols-3">
        <div className="rounded-lg border border-border px-2 py-2">
          <dt className="text-[11px] text-muted-foreground">Mastery</dt>
          <dd className="font-mono text-sm font-semibold">{formatPct(probability)}</dd>
        </div>
        <div className="rounded-lg border border-border px-2 py-2">
          <dt className="text-[11px] text-muted-foreground">Observations</dt>
          <dd className="font-mono text-sm font-semibold">{estimate.observation_count ?? 0}</dd>
        </div>
        <div className="rounded-lg border border-border px-2 py-2 sm:col-span-1 col-span-2">
          <dt className="text-[11px] text-muted-foreground">Signal</dt>
          <dd className="text-xs font-medium">{masteryLabel(probability)}</dd>
        </div>
      </dl>

      {known ? (
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted" aria-hidden="true">
          <div className="h-full rounded-full bg-primary" style={{ width: `${width}%` }} />
        </div>
      ) : (
        <p className="mt-3 text-xs text-muted-foreground">
          Missing evidence is not treated as zero mastery.
        </p>
      )}

      {estimate.explanation ? (
        <p className="mt-2 text-xs text-muted-foreground">{estimate.explanation}</p>
      ) : null}

      {estimate.parameters ? (
        <p className="mt-1 text-[11px] text-muted-foreground">
          Baseline params L0={estimate.parameters.p_l0}, T={estimate.parameters.p_t}, G=
          {estimate.parameters.p_g}, S={estimate.parameters.p_s} (not trained).
        </p>
      ) : null}
    </article>
  )
}

import { TrendingUp } from 'lucide-react'

function Change({ label, before, after, unit = '' }) {
  return (
    <div className="flex flex-col-reverse rounded-lg border border-border/60 px-3 py-2">
      <dt className="text-[11px] text-muted-foreground">{label}</dt>
      <dd className="text-sm tabular-nums text-muted-foreground">
        {before}
        {unit} <span aria-hidden="true">→</span>
        <span className="sr-only">to</span>{' '}
        <span className="font-semibold text-foreground">
          {after}
          {unit}
        </span>
      </dd>
    </div>
  )
}

export default function EvidenceUpdate({ message, confidence, evidence }) {
  return (
    <div className="space-y-3">
      {message && (
        <p className="flex items-start gap-2 rounded-lg bg-primary/5 px-3 py-2 text-xs leading-relaxed text-foreground">
          <TrendingUp className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
          {message}
        </p>
      )}
      <dl className="grid grid-cols-2 gap-2">
        <Change label="Confidence" before={confidence.before} after={confidence.after} unit="%" />
        <Change label="Learning evidence" before={evidence.before} after={evidence.after} />
      </dl>
    </div>
  )
}

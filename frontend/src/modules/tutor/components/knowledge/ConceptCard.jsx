import Badge from '@/shared/components/Badge.jsx'
import { cn } from '@/lib/utils'
import RequirementBar from './RequirementBar.jsx'
import { GAP_STATUS, getMeta } from '../../utils/statusMeta.js'

function Stat({ label, value, emphasis = false }) {
  return (
    <div>
      <dt className="text-[11px] text-muted-foreground">{label}</dt>
      <dd className={cn('text-sm font-semibold tabular-nums', emphasis ? 'text-destructive' : 'text-foreground')}>
        {value}
      </dd>
    </div>
  )
}

export default function ConceptCard({ concept }) {
  const { name, description, required, current, gap, status } = concept
  const meta = getMeta(GAP_STATUS, status)

  return (
    <article className="rounded-lg border border-border/60 bg-muted/20 p-3">
      <header className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold leading-snug text-foreground" title={description}>
          {name}
        </h3>
        <Badge tone={meta.tone} className="shrink-0">
          {meta.label}
        </Badge>
      </header>
      <RequirementBar
        label={name}
        current={current}
        required={required}
        barClass={meta.barClass}
        className="mt-2"
      />
      <dl className="mt-2 grid grid-cols-3 gap-2 text-center">
        <Stat label="Required" value={`${required}%`} />
        <Stat label="Current" value={`${current}%`} />
        <Stat label="Gap" value={`${gap}%`} emphasis={status === 'major_gap'} />
      </dl>
    </article>
  )
}

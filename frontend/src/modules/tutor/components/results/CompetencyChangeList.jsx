import Badge from '@/shared/components/Badge.jsx'
import RequirementBar from '../knowledge/RequirementBar.jsx'
import { GAP_STATUS, getMeta } from '../../utils/statusMeta.js'

function Stat({ label, children, emphasis }) {
  return (
    <div className="flex flex-col-reverse">
      <dt className="text-[11px] text-muted-foreground">{label}</dt>
      <dd className={emphasis ? 'text-base font-semibold text-foreground' : 'text-base font-medium text-muted-foreground'}>
        {children}
      </dd>
    </div>
  )
}

function CompetencyChange({ change }) {
  const statusAfter = getMeta(GAP_STATUS, change.statusAfter)
  const statusChanged = change.statusBefore !== change.statusAfter
  const delta = change.after - change.before

  return (
    <li className="rounded-lg border border-border/60 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-foreground">{change.name}</span>
        <Badge tone={statusAfter.tone}>{statusAfter.label}</Badge>
        {statusChanged && (
          <span className="text-[11px] text-muted-foreground">was {getMeta(GAP_STATUS, change.statusBefore).label}</span>
        )}
      </div>
      <dl className="mt-2 grid grid-cols-4 gap-2 tabular-nums">
        <Stat label="Before">{change.before}%</Stat>
        <Stat label="After" emphasis>
          {change.after}%
        </Stat>
        <Stat label="Change">
          <span className={delta > 0 ? 'text-emerald-700 dark:text-emerald-400' : undefined}>
            {delta > 0 ? '+' : ''}
            {delta}
          </span>
        </Stat>
        <Stat label="Required">{change.required}%</Stat>
      </dl>
      <RequirementBar
        label={change.name}
        current={change.after}
        required={change.required}
        barClass={statusAfter.barClass}
        className="mt-1"
      />
      <p className="text-[11px] tabular-nums text-muted-foreground">
        {change.gapAfter > 0 ? `Remaining gap: ${change.gapAfter}% (was ${change.gapBefore}%)` : 'Requirement met'}
      </p>
    </li>
  )
}

export default function CompetencyChangeList({ changes }) {
  return (
    <ul className="space-y-2">
      {changes.map((change) => (
        <CompetencyChange key={change.conceptId} change={change} />
      ))}
    </ul>
  )
}

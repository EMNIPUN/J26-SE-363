import { cn } from '@/lib/utils'

export default function GapSummary({ groups }) {
  return (
    <dl className="grid grid-cols-3 gap-2">
      {groups.map(({ status, meta, items }) => {
        const Icon = meta.icon
        return (
          <div key={status} className="flex flex-col-reverse rounded-lg border border-border/60 px-2 py-2 text-center">
            <dt className="text-[11px] text-muted-foreground">{meta.label}</dt>
            <dd className={cn('flex items-center justify-center gap-1 text-lg font-semibold tabular-nums', meta.textClass)}>
              {Icon && <Icon className="h-4 w-4" aria-hidden="true" />}
              {items.length}
            </dd>
          </div>
        )
      })}
    </dl>
  )
}

import { cn } from '@/lib/utils'
import { GAP_STATUS, getMeta } from '../../utils/statusMeta.js'

export default function GapItem({ concept }) {
  const { name, description, required, current, gap, status } = concept
  const meta = getMeta(GAP_STATUS, status)

  return (
    <article
      className={cn(
        'flex items-center justify-between gap-3 rounded-lg border border-l-4 border-border/60 bg-muted/20 px-3 py-2.5',
        meta.accentClass,
      )}
    >
      <div className="min-w-0">
        <h4 className="truncate text-sm font-semibold text-foreground" title={description}>
          {name}
        </h4>
        <p className="mt-0.5 text-xs tabular-nums text-muted-foreground">
          Current <span className="font-medium text-foreground">{current}%</span>
          <span aria-hidden="true"> · </span>
          Required <span className="font-medium text-foreground">{required}%</span>
        </p>
      </div>
      <p className={cn('shrink-0 text-right', meta.textClass)}>
        {gap > 0 ? (
          <>
            <span className="block text-sm font-semibold tabular-nums">{gap}%</span>
            <span className="block text-[11px] font-medium">below target</span>
          </>
        ) : (
          <span className="text-xs font-medium">Meets target</span>
        )}
      </p>
    </article>
  )
}

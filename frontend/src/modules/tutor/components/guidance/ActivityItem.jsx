import { Link } from 'react-router-dom'
import { ArrowRight, Clock, ListChecks } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import ProgressBar from '../common/ProgressBar.jsx'
import ItemBadges from './ItemBadges.jsx'
import { useTutorPaths } from '../../utils/tutorPaths.js'
import { ACTIVITY_KIND, getActivityActionLabel, getMeta } from '../../utils/statusMeta.js'

function ProgressLine({ title, progress, lastScore, done }) {
  if (lastScore != null) {
    return (
      <span className="font-medium text-foreground">
        Last score <span className="tabular-nums">{lastScore}%</span>
      </span>
    )
  }
  if (progress <= 0) return null
  return (
    <div className="w-full space-y-1.5">
      <span className="block tabular-nums">{done ? 'Completed' : `${progress}% complete`}</span>
      <ProgressBar value={progress} label={`${title} progress`} barClass={done ? 'bg-emerald-500' : 'bg-primary'} />
    </div>
  )
}

export default function ActivityItem({ item }) {
  const paths = useTutorPaths()
  const { id, kind, title, summary, level, estimatedMinutes, itemCount, matchesLevel, recommended, challenge } = item
  const kindMeta = getMeta(ACTIVITY_KIND, kind)
  const KindIcon = kindMeta.icon

  return (
    <article
      className={cn(
        'flex h-full flex-col gap-3 rounded-lg border bg-card p-4',
        recommended ? 'border-primary/40 ring-1 ring-primary/10' : 'border-border/60',
      )}
    >
      <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-primary">
        {KindIcon && <KindIcon className="h-3.5 w-3.5" aria-hidden="true" />}
        {kindMeta.label}
      </p>
      <ItemBadges level={level} matchesLevel={matchesLevel} recommended={recommended} challenge={challenge} />
      <div className="flex-1">
        <h4 className="text-sm font-semibold leading-snug text-foreground">{title}</h4>
        {summary && <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{summary}</p>}
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] text-muted-foreground">
        <span className="flex items-center gap-1">
          <Clock className="h-3.5 w-3.5" aria-hidden="true" />
          {estimatedMinutes} min
        </span>
        {itemCount != null && kindMeta.countLabel && (
          <span className="flex items-center gap-1">
            <ListChecks className="h-3.5 w-3.5" aria-hidden="true" />
            {itemCount} {kindMeta.countLabel}
          </span>
        )}
        <ProgressLine {...item} />
      </div>
      <Button asChild size="sm" variant={recommended ? 'default' : 'outline'} className="w-full">
        <Link to={paths.activity(id)}>
          {getActivityActionLabel(kindMeta, item)}
          <span className="sr-only">: {title}</span>
          <ArrowRight aria-hidden="true" />
        </Link>
      </Button>
    </article>
  )
}

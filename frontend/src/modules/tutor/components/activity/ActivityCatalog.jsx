import { useId } from 'react'
import { Inbox } from 'lucide-react'
import Badge from '@/shared/components/Badge.jsx'
import QueryState from '../common/QueryState.jsx'
import LoadingState from '../common/LoadingState.jsx'
import RequirementBar from '../knowledge/RequirementBar.jsx'
import ActivityItem from '../guidance/ActivityItem.jsx'
import { useActivityCatalog } from '../../hooks/useLearning.js'
import { GAP_STATUS, LEVEL, getMeta } from '../../utils/statusMeta.js'

function ConceptGroup({ group }) {
  const headingId = useId()
  const status = getMeta(GAP_STATUS, group.status)
  const level = getMeta(LEVEL, group.level)

  return (
    <section
      aria-labelledby={headingId}
      className="rounded-xl border border-border/60 bg-card p-4 text-card-foreground card-elevated"
    >
      <header className="mb-3 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id={headingId} className="text-base font-semibold text-foreground">
            {group.name}
          </h2>
          <Badge tone={status.tone}>{status.label}</Badge>
          <Badge tone={group.suggested ? 'primary' : 'neutral'}>
            {group.suggested ? 'Suggested for this gap' : 'Optional'}
          </Badge>
          <span className="ml-auto flex items-center gap-1.5 text-xs text-muted-foreground">
            Your level
            <Badge tone={level.tone}>{level.label}</Badge>
          </span>
        </div>
        <p className="text-xs tabular-nums text-muted-foreground">
          Current <span className="font-medium text-foreground">{group.current}%</span>
          <span aria-hidden="true"> · </span>
          Required <span className="font-medium text-foreground">{group.required}%</span>
        </p>
        <RequirementBar
          label={group.name}
          current={group.current}
          required={group.required}
          barClass={status.barClass}
        />
        <p className="text-xs leading-relaxed text-muted-foreground">{group.suggestionSummary}</p>
      </header>
      <ul className="grid gap-3 @2xl:grid-cols-2 @6xl:grid-cols-3">
        {group.items.map((item) => (
          <li key={item.id}>
            <ActivityItem item={item} />
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function ActivityCatalog({ kind, emptyTitle, emptyDescription }) {
  const catalogQuery = useActivityCatalog(kind)

  return (
    <QueryState
      query={catalogQuery}
      isEmpty={(data) => !data?.concepts?.length}
      loading={<LoadingState rows={6} label="Loading activities" />}
      errorTitle="Could not load activities"
      emptyIcon={Inbox}
      emptyTitle={emptyTitle}
      emptyDescription={emptyDescription}
    >
      {(catalog) => (
        <div className="flex flex-col gap-4">
          {catalog.concepts.map((group) => (
            <ConceptGroup key={group.conceptId} group={group} />
          ))}
        </div>
      )}
    </QueryState>
  )
}

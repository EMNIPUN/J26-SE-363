import { TriangleAlert } from 'lucide-react'
import { cn } from '@/lib/utils'
import ContextSection from '../layout/ContextSection.jsx'
import QueryState from '../common/QueryState.jsx'
import LoadingState from '../common/LoadingState.jsx'
import GapSummary from './GapSummary.jsx'
import GapItem from './GapItem.jsx'
import { useKnowledgeGaps } from '../../hooks/useTutorOverview.js'
import { GAP_STATUS } from '../../utils/statusMeta.js'

// Groups the backend's classified gaps by status, keeping the backend's
// ordering inside each group.
function groupByStatus(gaps) {
  return Object.entries(GAP_STATUS).map(([status, meta]) => ({
    status,
    meta,
    items: gaps.filter((gap) => gap.status === status),
  }))
}

export default function KnowledgeGaps() {
  const knowledgeGapsQuery = useKnowledgeGaps()

  return (
    <ContextSection
      icon={TriangleAlert}
      title="Knowledge Gaps"
      description="Where your competency is below what the task requires"
    >
      <QueryState
        query={knowledgeGapsQuery}
        loading={<LoadingState rows={4} label="Loading knowledge gaps" />}
        errorTitle="Could not load knowledge gaps"
        emptyIcon={TriangleAlert}
        emptyTitle="No gaps to show"
        emptyDescription="Gaps appear once your current task is mapped to the concepts it requires."
      >
        {(gaps) => {
          const groups = groupByStatus(gaps)
          return (
            <div className="space-y-4">
              <GapSummary groups={groups} />
              {groups
                .filter(({ items }) => items.length > 0)
                .map(({ status, meta, items }) => {
                  const Icon = meta.icon
                  return (
                    <section key={status} aria-labelledby={`gap-group-${status}`}>
                      <h3
                        id={`gap-group-${status}`}
                        className={cn('mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider', meta.textClass)}
                      >
                        {Icon && <Icon className="h-3.5 w-3.5" aria-hidden="true" />}
                        {meta.label}
                      </h3>
                      <ul className="space-y-2">
                        {items.map((concept) => (
                          <li key={concept.conceptId}>
                            <GapItem concept={concept} />
                          </li>
                        ))}
                      </ul>
                    </section>
                  )
                })}
            </div>
          )
        }}
      </QueryState>
    </ContextSection>
  )
}

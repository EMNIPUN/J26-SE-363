import { BookOpenCheck } from 'lucide-react'
import ContextSection from '../layout/ContextSection.jsx'
import QueryState from '../common/QueryState.jsx'
import LoadingState from '../common/LoadingState.jsx'
import ConceptCard from './ConceptCard.jsx'
import { useRequiredKnowledge } from '../../hooks/useTutorOverview.js'

function BarLegend() {
  return (
    <p className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-4 rounded-full bg-muted-foreground/40" aria-hidden="true" />
        Current competency
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-3 w-0.5 rounded-full bg-foreground/70" aria-hidden="true" />
        Required for task
      </span>
    </p>
  )
}

export default function RequiredKnowledge() {
  const requiredKnowledgeQuery = useRequiredKnowledge()

  return (
    <ContextSection icon={BookOpenCheck} title="Required Knowledge" description="Concepts your current task depends on">
      <QueryState
        query={requiredKnowledgeQuery}
        loading={<LoadingState rows={4} label="Loading required knowledge" />}
        errorTitle="Could not load required knowledge"
        emptyIcon={BookOpenCheck}
        emptyTitle="No required concepts"
        emptyDescription="Concepts will appear here once your current task is mapped to the knowledge it needs."
      >
        {(concepts) => (
          <>
            <ul className="space-y-2.5">
              {concepts.map((concept) => (
                <li key={concept.conceptId}>
                  <ConceptCard concept={concept} />
                </li>
              ))}
            </ul>
            <BarLegend />
          </>
        )}
      </QueryState>
    </ContextSection>
  )
}

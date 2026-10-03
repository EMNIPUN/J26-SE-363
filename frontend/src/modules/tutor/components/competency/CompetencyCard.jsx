import { Gauge } from 'lucide-react'
import ContextSection from '../layout/ContextSection.jsx'
import QueryState from '../common/QueryState.jsx'
import LoadingState from '../common/LoadingState.jsx'
import CompetencyProgress from './CompetencyProgress.jsx'
import ConfidenceIndicator from './ConfidenceIndicator.jsx'
import EvidenceSummary from './EvidenceSummary.jsx'
import { useCompetencies } from '../../hooks/useTutorOverview.js'

export default function CompetencyCard() {
  const competenciesQuery = useCompetencies()

  return (
    <ContextSection icon={Gauge} title="Competency" description="Estimated from your learning evidence">
      <QueryState
        query={competenciesQuery}
        isEmpty={(data) => !data?.items?.length}
        loading={<LoadingState rows={5} label="Loading competency" />}
        errorTitle="Could not load your competency"
        emptyIcon={Gauge}
        emptyTitle="No competency estimate yet"
        emptyDescription="Complete a lesson, exercise or quiz so the Tutor can estimate your competency."
      >
        {({ confidence, evidence, updatedAt, items }) => (
          <div className="space-y-4">
            <ConfidenceIndicator value={confidence} />
            <ul className="space-y-3">
              {items.map((item) => (
                <li key={item.conceptId}>
                  <CompetencyProgress name={item.name} score={item.score} />
                </li>
              ))}
            </ul>
            <div className="border-t border-border pt-3">
              <EvidenceSummary evidence={evidence} updatedAt={updatedAt} />
            </div>
          </div>
        )}
      </QueryState>
    </ContextSection>
  )
}

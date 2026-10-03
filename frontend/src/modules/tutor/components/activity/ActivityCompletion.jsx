import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, CircleCheck, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import Badge from '@/shared/components/Badge.jsx'
import ContextSection from '../layout/ContextSection.jsx'
import CompetencyChangeList from '../results/CompetencyChangeList.jsx'
import EvidenceUpdate from '../results/EvidenceUpdate.jsx'
import NextRecommendation from '../results/NextRecommendation.jsx'
import { useTutorPaths } from '../../utils/tutorPaths.js'

export default function ActivityCompletion({ result, onReopen }) {
  const paths = useTutorPaths()

  return (
    <div className="grid gap-4 @4xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <ContextSection
        icon={CircleCheck}
        title="Activity completed"
        description={`Result received from ${result.platform}`}
        action={<Badge tone="success">Score {result.score}%</Badge>}
      >
        <div className="space-y-3">
          <EvidenceUpdate message={result.message} confidence={result.confidence} evidence={result.evidence} />
          <CompetencyChangeList changes={result.changes} />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button asChild size="sm">
            <Link to={paths.results(result.assessmentId)}>
              View full results
              <ArrowRight aria-hidden="true" />
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to={paths.sprintGuidance}>
              <ArrowLeft aria-hidden="true" />
              Sprint Guidance
            </Link>
          </Button>
          <Button variant="ghost" size="sm" onClick={onReopen}>
            <RotateCcw aria-hidden="true" />
            Open activity again
          </Button>
        </div>
      </ContextSection>

      <NextRecommendation recommendation={result.nextRecommendation} />
    </div>
  )
}

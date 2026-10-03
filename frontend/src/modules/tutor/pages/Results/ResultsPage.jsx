import { Link, useParams } from 'react-router-dom'
import { Award, BarChart3, Bot, Compass, History, RotateCcw, TrendingUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import TutorHeader from '../../components/tutor/TutorHeader.jsx'
import ContextSection from '../../components/layout/ContextSection.jsx'
import QueryState from '../../components/common/QueryState.jsx'
import LoadingState from '../../components/common/LoadingState.jsx'
import ResultSummary from '../../components/results/ResultSummary.jsx'
import ConceptPerformance from '../../components/results/ConceptPerformance.jsx'
import CompetencyChangeList from '../../components/results/CompetencyChangeList.jsx'
import EvidenceUpdate from '../../components/results/EvidenceUpdate.jsx'
import NextRecommendation from '../../components/results/NextRecommendation.jsx'
import { useUpdatedCompetency } from '../../hooks/useResults.js'
import { useTutorPaths } from '../../utils/tutorPaths.js'
import { ACTIVITY_KIND, getMeta } from '../../utils/statusMeta.js'

function ResultActions({ result }) {
  const paths = useTutorPaths()
  const kind = getMeta(ACTIVITY_KIND, result.assessmentType)

  return (
    <ContextSection icon={Compass} title="Keep going" description="Continue your learning plan or ask the Tutor">
      <div className="grid gap-2">
        <Button asChild variant="outline" size="sm" className="justify-start">
          <Link to={paths.sprintGuidance}>
            <Compass aria-hidden="true" />
            Back to Sprint Guidance
          </Link>
        </Button>
        <Button asChild variant="outline" size="sm" className="justify-start">
          <Link to={paths.activity(result.activityId)}>
            <RotateCcw aria-hidden="true" />
            {kind.doneLabel ?? 'Open again'}
            <span className="sr-only">: {result.title}</span>
          </Link>
        </Button>
        <Button asChild variant="outline" size="sm" className="justify-start">
          <Link to={paths.chat}>
            <Bot aria-hidden="true" />
            Ask the Tutor about this result
          </Link>
        </Button>
      </div>
    </ContextSection>
  )
}

function ResultDetails({ result }) {
  return (
    <div className="grid items-start gap-4 @4xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <div className="flex flex-col gap-4">
        <ContextSection icon={Award} title="Result" description={`Reported by ${result.platform}`}>
          <ResultSummary result={result} />
        </ContextSection>
        <ContextSection
          icon={BarChart3}
          title="Concept Performance"
          description="Your score on each concept this activity assessed"
        >
          <ConceptPerformance items={result.conceptPerformance} />
        </ContextSection>
        <ContextSection icon={TrendingUp} title="Updated Competency" description="Before and after this activity">
          <div className="space-y-3">
            <EvidenceUpdate message={result.message} confidence={result.confidence} evidence={result.evidence} />
            <CompetencyChangeList changes={result.changes} />
          </div>
        </ContextSection>
      </div>
      <div className="flex flex-col gap-4">
        <NextRecommendation recommendation={result.nextRecommendation} />
        <ResultActions result={result} />
      </div>
    </div>
  )
}

export default function ResultsPage() {
  const { id } = useParams()
  const paths = useTutorPaths()
  const resultQuery = useUpdatedCompetency(id)

  return (
    <div className="flex flex-col gap-6">
      <TutorHeader
        icon={Award}
        title="Assessment Results"
        description="How this activity changed your competency, your knowledge gaps and the Tutor’s next recommendation."
        actions={
          <Button asChild variant="outline" size="sm">
            <Link to={paths.progress}>
              <History aria-hidden="true" />
              All results
            </Link>
          </Button>
        }
      />
      <QueryState
        query={resultQuery}
        loading={<LoadingState rows={8} label="Loading your result" />}
        errorTitle="Could not load this result"
      >
        {(result) => <ResultDetails result={result} />}
      </QueryState>
    </div>
  )
}

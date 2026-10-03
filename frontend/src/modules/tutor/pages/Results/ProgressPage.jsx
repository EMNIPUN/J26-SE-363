import { Link } from 'react-router-dom'
import { Compass, TrendingUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import TutorHeader from '../../components/tutor/TutorHeader.jsx'
import CompetencyCard from '../../components/competency/CompetencyCard.jsx'
import KnowledgeGaps from '../../components/knowledge/KnowledgeGaps.jsx'
import AssessmentHistory from '../../components/results/AssessmentHistory.jsx'
import { useTutorPaths } from '../../utils/tutorPaths.js'

export default function ProgressPage() {
  const paths = useTutorPaths()

  return (
    <div className="flex flex-col gap-6">
      <TutorHeader
        icon={TrendingUp}
        title="Progress & Results"
        description="Your activity results and how they have changed your competency and knowledge gaps."
        actions={
          <Button asChild variant="outline" size="sm">
            <Link to={paths.sprintGuidance}>
              <Compass aria-hidden="true" />
              Sprint Guidance
            </Link>
          </Button>
        }
      />
      <div className="grid items-start gap-4 @4xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <AssessmentHistory />
        <div className="flex flex-col gap-4">
          <CompetencyCard />
          <KnowledgeGaps />
        </div>
      </div>
    </div>
  )
}

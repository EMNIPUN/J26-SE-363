import { Link } from 'react-router-dom'
import { ClipboardCheck, History } from 'lucide-react'
import { Button } from '@/components/ui/button'
import TutorHeader from '../../components/tutor/TutorHeader.jsx'
import ActivityCatalog from '../../components/activity/ActivityCatalog.jsx'
import { useTutorPaths } from '../../utils/tutorPaths.js'

export default function AssessmentsPage() {
  const paths = useTutorPaths()

  return (
    <div className="flex flex-col gap-6">
      <TutorHeader
        icon={ClipboardCheck}
        title="Assessments"
        description="Adaptive quizzes that adjust to your answers. Each result becomes new evidence of your competency."
        actions={
          <Button asChild variant="outline" size="sm">
            <Link to={paths.progress}>
              <History aria-hidden="true" />
              Past results
            </Link>
          </Button>
        }
      />
      <ActivityCatalog
        kind="quiz"
        emptyTitle="No quizzes yet"
        emptyDescription="Adaptive quizzes appear once your current task is mapped to the concepts it requires."
      />
    </div>
  )
}

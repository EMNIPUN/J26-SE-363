import { Link } from 'react-router-dom'
import { Code2, Compass } from 'lucide-react'
import { Button } from '@/components/ui/button'
import TutorHeader from '../../components/tutor/TutorHeader.jsx'
import ActivityCatalog from '../../components/activity/ActivityCatalog.jsx'
import { useTutorPaths } from '../../utils/tutorPaths.js'

export default function ExercisesPage() {
  const paths = useTutorPaths()

  return (
    <div className="flex flex-col gap-6">
      <TutorHeader
        icon={Code2}
        title="Practice Exercises"
        description="Hands-on coding exercises for each concept in your current task, ordered by your knowledge gaps. Your results update your competency."
        actions={
          <Button asChild variant="outline" size="sm">
            <Link to={paths.sprintGuidance}>
              <Compass aria-hidden="true" />
              Sprint Guidance
            </Link>
          </Button>
        }
      />
      <ActivityCatalog
        kind="exercise"
        emptyTitle="No coding exercises yet"
        emptyDescription="Coding exercises appear once your current task is mapped to the concepts it requires."
      />
    </div>
  )
}

import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'
import { Button } from '@/components/ui/button'
import TutorHeader from '../../components/tutor/TutorHeader.jsx'
import TutorChat from '../../components/tutor/TutorChat.jsx'
import { useTutorPaths } from '../../utils/tutorPaths.js'

export default function TutorPage() {
  const paths = useTutorPaths()

  return (
    <div className="flex flex-col gap-6">
      <TutorHeader
        title="SELVIA AI Tutor"
        description="Personalized support based on your project, learning evidence, and current competency."
        actions={
          <Button asChild variant="outline" size="sm">
            <Link to={paths.sprintGuidance}>
              <Compass aria-hidden="true" />
              Sprint Guidance
            </Link>
          </Button>
        }
      />
      <section
        aria-label="Tutor conversation"
        className="h-[72svh] min-h-[440px] @4xl:h-[calc(100svh-15rem)] @4xl:min-h-[520px]"
      >
        <TutorChat />
      </section>
    </div>
  )
}

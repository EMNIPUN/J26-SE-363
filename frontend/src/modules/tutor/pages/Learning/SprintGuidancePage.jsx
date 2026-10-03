import { useSearchParams } from 'react-router-dom'
import { Compass, Gauge, GraduationCap } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import TutorHeader from '../../components/tutor/TutorHeader.jsx'
import ProjectContext from '../../components/tutor/ProjectContext.jsx'
import RequiredKnowledge from '../../components/knowledge/RequiredKnowledge.jsx'
import CompetencyCard from '../../components/competency/CompetencyCard.jsx'
import KnowledgeGaps from '../../components/knowledge/KnowledgeGaps.jsx'
import RecommendationCard from '../../components/recommendation/RecommendationCard.jsx'
import LearningPlan from '../../components/guidance/LearningPlan.jsx'
import LearningLoop from '../../components/guidance/LearningLoop.jsx'

const TABS = { plan: 'plan', overview: 'overview' }

export default function SprintGuidancePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') === TABS.overview ? TABS.overview : TABS.plan

  const handleTabChange = (value) => {
    setSearchParams(value === TABS.plan ? {} : { tab: value }, { replace: true })
  }

  return (
    <div className="flex flex-col gap-6">
      <TutorHeader
        icon={Compass}
        title="Sprint Guidance"
        description="Learning material, adaptive quizzes and coding exercises chosen from your knowledge gaps for the current sprint task."
      />
      <LearningLoop />
      <Tabs value={tab} onValueChange={handleTabChange} className="gap-5">
        <TabsList aria-label="Sprint guidance views" className="h-10 self-start">
          <TabsTrigger value={TABS.plan} className="h-8 gap-1.5">
            <GraduationCap className="h-3.5 w-3.5" aria-hidden="true" />
            Learning Plan
          </TabsTrigger>
          <TabsTrigger value={TABS.overview} className="h-8 gap-1.5">
            <Gauge className="h-3.5 w-3.5" aria-hidden="true" />
            Competency &amp; Gaps
          </TabsTrigger>
        </TabsList>

        <TabsContent value={TABS.plan} className="mt-0">
          <LearningPlan />
        </TabsContent>

        {/* Sections flow in workflow order down CSS columns, which avoids the
            empty space a grid leaves between cards of very different heights. */}
        <TabsContent value={TABS.overview} className="mt-0">
          <div className="columns-1 gap-4 @2xl:columns-2 [&>*]:mb-4 [&>*]:break-inside-avoid">
            <ProjectContext />
            <RequiredKnowledge />
            <CompetencyCard />
            <KnowledgeGaps />
            <RecommendationCard />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

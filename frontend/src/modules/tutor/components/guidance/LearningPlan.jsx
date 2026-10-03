import { useState } from 'react'
import { Compass, Target } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'
import QueryState from '../common/QueryState.jsx'
import LoadingState from '../common/LoadingState.jsx'
import ConceptPlan from './ConceptPlan.jsx'
import { useSprintGuidance } from '../../hooks/useLearning.js'
import { GAP_STATUS, LEVEL, getMeta } from '../../utils/statusMeta.js'

function ConceptTrigger({ concept, isFocus }) {
  const status = getMeta(GAP_STATUS, concept.status)
  const level = getMeta(LEVEL, concept.level)

  return (
    <TabsTrigger
      value={concept.conceptId}
      className="h-auto flex-col items-start gap-0.5 rounded-lg border border-border/60 bg-card px-3 py-2 text-left data-[state=active]:border-primary/50 data-[state=active]:bg-primary/5 data-[state=active]:shadow-none"
    >
      <span className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
        <span className={cn('h-2 w-2 rounded-full', status.barClass)} aria-hidden="true" />
        {concept.name}
        {isFocus && <Target className="h-3 w-3 text-primary" aria-hidden="true" />}
      </span>
      <span className="text-[11px] font-normal text-muted-foreground">
        {level.label} · <span className="tabular-nums">{concept.current}%</span>
      </span>
      <span className="sr-only">
        {status.label}
        {isFocus ? ', current Tutor focus' : ''}
      </span>
    </TabsTrigger>
  )
}

function ConceptTabs({ guidance }) {
  const { concepts, focusConceptId, platform } = guidance
  const [selectedId, setSelectedId] = useState(null)
  const activeId = concepts.some((c) => c.conceptId === selectedId)
    ? selectedId
    : (focusConceptId ?? concepts[0].conceptId)

  return (
    <Tabs value={activeId} onValueChange={setSelectedId} className="gap-5">
      <div>
        <p className="mb-2 text-xs text-muted-foreground">
          Choose a concept from your current task.
          {focusConceptId && (
            <>
              {' '}
              <Target className="inline h-3 w-3 align-[-2px] text-primary" aria-hidden="true" /> marks the Tutor’s
              current focus.
            </>
          )}
        </p>
        <TabsList aria-label="Concepts" className="h-auto w-full flex-wrap justify-start gap-2 bg-transparent p-0">
          {concepts.map((concept) => (
            <ConceptTrigger key={concept.conceptId} concept={concept} isFocus={concept.conceptId === focusConceptId} />
          ))}
        </TabsList>
      </div>
      {concepts.map((concept) => (
        <TabsContent key={concept.conceptId} value={concept.conceptId} className="mt-0">
          <ConceptPlan plan={concept} platformName={platform?.name} />
        </TabsContent>
      ))}
    </Tabs>
  )
}

export default function LearningPlan() {
  const guidanceQuery = useSprintGuidance()

  return (
    <QueryState
      query={guidanceQuery}
      isEmpty={(data) => !data?.concepts?.length}
      loading={<LoadingState rows={6} label="Loading your learning plan" />}
      errorTitle="Could not load your learning plan"
      emptyIcon={Compass}
      emptyTitle="No learning plan yet"
      emptyDescription="Your plan appears once your current task is mapped to the concepts it requires."
    >
      {(guidance) => <ConceptTabs guidance={guidance} />}
    </QueryState>
  )
}

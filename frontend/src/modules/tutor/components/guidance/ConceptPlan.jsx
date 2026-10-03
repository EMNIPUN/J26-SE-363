import { BookOpen, Dumbbell, Globe, Info, Sparkles } from 'lucide-react'
import Badge from '@/shared/components/Badge.jsx'
import RequirementBar from '../knowledge/RequirementBar.jsx'
import PlanSection from './PlanSection.jsx'
import ActivityItem from './ActivityItem.jsx'
import ExternalResourceItem from './ExternalResourceItem.jsx'
import { GAP_STATUS, LEVEL, getMeta } from '../../utils/statusMeta.js'

function LevelSummary({ plan }) {
  const status = getMeta(GAP_STATUS, plan.status)
  const level = getMeta(LEVEL, plan.level)

  return (
    <div className="rounded-xl border border-border/60 bg-card p-4 card-elevated">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-base font-semibold text-foreground">{plan.name}</h3>
        <Badge tone={status.tone}>{status.label}</Badge>
        <span className="ml-auto flex items-center gap-1.5 text-xs text-muted-foreground">
          Your level
          <Badge tone={level.tone}>{level.label}</Badge>
        </span>
      </div>
      <p className="mt-1 text-xs tabular-nums text-muted-foreground">
        Current <span className="font-medium text-foreground">{plan.current}%</span>
        <span aria-hidden="true"> · </span>
        Required <span className="font-medium text-foreground">{plan.required}%</span>
      </p>
      <RequirementBar
        label={plan.name}
        current={plan.current}
        required={plan.required}
        barClass={status.barClass}
        className="mt-2"
      />
      {plan.suggestionSummary && (
        <p className="mt-3 flex items-start gap-2 rounded-lg bg-muted/50 px-3 py-2 text-xs leading-relaxed text-muted-foreground">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
          {plan.suggestionSummary}
        </p>
      )}
    </div>
  )
}

const renderActivity = (item) => <ActivityItem item={item} />

export default function ConceptPlan({ plan, platformName }) {
  const { learning, practice, challenge, webResources } = plan.suggestions
  const onPlatform = platformName ? ` in ${platformName}` : ''

  return (
    <div className="space-y-6">
      <LevelSummary plan={plan} />
      {learning && (
        <PlanSection
          icon={BookOpen}
          title="Learning Material"
          description={`${plan.levelSummary} Opens${onPlatform}.`}
          items={learning}
          emptyMessage="No learning material covers this concept yet. Try the web resources below."
          renderItem={renderActivity}
        />
      )}
      {practice && (
        <PlanSection
          icon={Dumbbell}
          title="Adaptive Quizzes & Coding Exercises"
          description="Questions adapt to your answers. Your results update your competency and knowledge gap."
          items={practice}
          emptyMessage="No quiz or coding exercise covers this concept yet. Ask the Tutor in the chat for a practice activity."
          renderItem={renderActivity}
        />
      )}
      {challenge && (
        <PlanSection
          icon={Sparkles}
          title="Optional Challenge"
          description="You already meet the requirement. Take this only if you want to go further."
          items={challenge}
          emptyMessage="No challenge is available for this concept."
          renderItem={renderActivity}
        />
      )}
      {webResources && (
        <PlanSection
          icon={Globe}
          title="Web Resources"
          description="Trusted references to read alongside the learning material, matched to your level"
          items={webResources}
          emptyMessage="No web resources for this concept yet."
          renderItem={(resource) => <ExternalResourceItem resource={resource} />}
        />
      )}
    </div>
  )
}

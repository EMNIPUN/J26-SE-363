import { Link } from 'react-router-dom'
import { Check, Lock } from 'lucide-react'
import { Progress } from '@/components/ui/progress'
import { useTeamPath } from '@/shared/hooks/useTeamPath.js'
import { usePlanningData } from '../context/usePlanningData.js'
import { computeStageStats, STAGE_ORDER } from '../stageStats.js'

export default function WorkflowStepper({ current, variant = 'compact' }) {
  const team = useTeamPath()
  const { requirements, userStories, estimations, kanbanTasks } = usePlanningData()
  const stats = computeStageStats({ requirements, userStories, estimations, kanbanTasks })
  const stages = STAGE_ORDER.map((key) => stats[key])

  if (variant === 'full') {
    return (
      <div className="space-y-1">
        {stages.map((stage, i) => (
          <Link
            key={stage.key}
            to={team(stage.to)}
            className="flex items-start gap-3.5 group rounded-lg -mx-2 px-2 py-2.5 hover:bg-muted/50 transition-colors"
          >
            <span
              className={`mt-0.5 h-7 w-7 rounded-full flex items-center justify-center shrink-0 text-[11px] font-bold transition-colors ${
                stage.complete
                  ? 'bg-emerald-500 text-white'
                  : stage.blocked
                    ? 'bg-muted text-muted-foreground'
                    : 'bg-primary/10 text-primary group-hover:bg-primary/15'
              }`}
            >
              {stage.complete ? <Check className="h-3.5 w-3.5" strokeWidth={3} /> : stage.blocked ? <Lock className="h-3 w-3" /> : i + 1}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                  {stage.label}
                </span>
                <span className="text-xs font-semibold text-muted-foreground shrink-0">{stage.percent}%</span>
              </div>
              <Progress
                value={stage.percent}
                className={`h-1.5 mt-1.5 ${stage.complete ? '[&>div]:bg-emerald-500' : stage.blocked ? '[&>div]:bg-muted-foreground/40' : ''}`}
              />
              <p className="text-xs text-muted-foreground mt-1.5">{stage.caption}</p>
            </div>
          </Link>
        ))}
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2 sm:gap-3 overflow-x-auto column-scroll-contain pb-1">
      {stages.map((stage, i) => {
        const isCurrent = stage.key === current
        const isDone = stage.complete
        return (
          <div key={stage.key} className="flex items-center gap-2 sm:gap-3 shrink-0">
            <Link
              to={team(stage.to)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium transition-colors ${
                isCurrent
                  ? 'border-primary bg-primary/10 text-primary'
                  : isDone
                    ? 'border-emerald-500/30 bg-emerald-500/5 text-emerald-700 dark:text-emerald-400'
                    : stage.blocked
                      ? 'border-border bg-muted/40 text-muted-foreground'
                      : 'border-border text-muted-foreground hover:text-foreground hover:bg-muted/40'
              }`}
            >
              <span
                className={`h-4 w-4 rounded-full flex items-center justify-center shrink-0 ${
                  isDone ? 'bg-emerald-500 text-white' : isCurrent ? 'bg-primary text-primary-foreground' : 'border border-current'
                }`}
              >
                {isDone ? <Check className="h-2.5 w-2.5" strokeWidth={3} /> : stage.blocked && !isCurrent ? (
                  <Lock className="h-2.5 w-2.5" />
                ) : null}
              </span>
              <span>{stage.label}</span>
              <span className="text-[10px] text-muted-foreground font-normal">{stage.percent}%</span>
            </Link>
            {i < stages.length - 1 && <span className="h-px w-4 sm:w-6 bg-border shrink-0" />}
          </div>
        )
      })}
    </div>
  )
}

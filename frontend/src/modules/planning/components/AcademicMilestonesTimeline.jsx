import { CheckCircle2, Clock, Calendar } from 'lucide-react'
import Card from '../../../shared/components/Card.jsx'
import Badge from '../../../shared/components/Badge.jsx'
import { ACADEMIC_MILESTONES } from '../data/lmsAcademicData.js'

export default function AcademicMilestonesTimeline() {
  const completedCount = ACADEMIC_MILESTONES.filter((m) => m.status === 'Completed').length
  const totalWeight = ACADEMIC_MILESTONES.reduce((acc, m) => acc + m.weightValue, 0)
  const completedWeight = ACADEMIC_MILESTONES.filter((m) => m.status === 'Completed').reduce(
    (acc, m) => acc + m.weightValue,
    0,
  )

  return (
    <Card className="p-5 overflow-hidden">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 mb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1 rounded bg-primary/10 text-primary">
              <Calendar className="h-4 w-4" />
            </span>
            <h3 className="text-base font-semibold text-foreground">Capstone Academic Milestones</h3>
            <Badge tone="primary" className="text-xs">
              {completedCount} of {ACADEMIC_MILESTONES.length} Completed
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Official curriculum deliverables and assessment deadlines for SE4010 Capstone (2026/S1)
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right">
            <p className="text-[11px] text-muted-foreground font-medium">Evaluation Weight Progress</p>
            <p className="text-sm font-bold text-foreground">
              {completedWeight}% / {totalWeight}% Secured
            </p>
          </div>
          <div className="h-8 w-24 bg-muted rounded-full overflow-hidden p-0.5 border border-border">
            <div
              className="h-full bg-emerald-500 rounded-full transition-all duration-500"
              style={{ width: `${(completedWeight / totalWeight) * 100}%` }}
            />
          </div>
        </div>
      </div>

      <div className="relative">
        {/* Horizontal connector line on desktop */}
        <div className="hidden md:block absolute top-[28px] left-[40px] right-[40px] h-0.5 bg-border -z-0" />

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 relative z-10">
          {ACADEMIC_MILESTONES.map((m, idx) => {
            const isCompleted = m.status === 'Completed'
            const isCurrent = m.isCurrent

            return (
              <div
                key={m.id}
                className={`rounded-xl border transition-all duration-200 ${
                  isCurrent
                    ? 'border-primary bg-primary/5 shadow-sm ring-1 ring-primary/20'
                    : isCompleted
                      ? 'border-border bg-card/80 hover:bg-muted/40'
                      : 'border-border/60 bg-muted/20 opacity-85'
                }`}
              >
                <div className="p-3.5">
                  <div className="flex items-center justify-between mb-2">
                    <span
                      className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-colors ${
                        isCompleted
                          ? 'bg-emerald-500 text-white'
                          : isCurrent
                            ? 'bg-primary text-primary-foreground animate-pulse'
                            : 'bg-muted text-muted-foreground border border-border'
                      }`}
                    >
                      {isCompleted ? <CheckCircle2 className="h-4 w-4" /> : idx + 1}
                    </span>

                    <Badge
                      tone={isCompleted ? 'success' : isCurrent ? 'primary' : 'neutral'}
                      className="text-[10px] px-1.5 py-0"
                    >
                      {m.weight} Weight
                    </Badge>
                  </div>

                  <p className="text-xs font-bold text-foreground leading-snug truncate" title={m.title}>
                    {m.code}: {m.title}
                  </p>

                  <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mt-1.5">
                    <Clock className="h-3 w-3 shrink-0" />
                    <span className="truncate">{m.dueDate}</span>
                  </div>

                  <div className="mt-2 pt-2 border-t border-border/50 text-[11px]">
                    <span
                      className={`font-semibold ${
                        isCompleted
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : isCurrent
                            ? 'text-primary'
                            : 'text-muted-foreground'
                      }`}
                    >
                      {m.status}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </Card>
  )
}

import { useState } from 'react'
import { ChevronDown, Clock, Play, BookOpen } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { CONCEPTS, MATERIALS, TASKS } from '../data/tutorWorkspace.js'

export default function RecommendedNextActionCard({
  recommendation,
  onStartPractice,
  onViewMaterial,
}) {
  const [open, setOpen] = useState(false)
  if (!recommendation) return null

  const concept = CONCEPTS[recommendation.conceptId]
  const task = TASKS.find((item) => item.id === recommendation.taskId)
  const material = MATERIALS[recommendation.materialId]

  return (
    <section className="rounded-xl border border-primary/30 bg-card p-5 shadow-xs">
      <p className="text-xs font-semibold uppercase tracking-wide text-primary">Recommended next action</p>
      <h2 className="mt-1 text-lg font-semibold text-foreground">{recommendation.intervention}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">{recommendation.explanation}</p>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs text-muted-foreground">Target concept</dt>
          <dd className="font-medium">{concept?.label || '—'}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Project task</dt>
          <dd className="font-medium">{task?.title || '—'}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Duration</dt>
          <dd className="flex items-center gap-1 font-medium">
            <Clock className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
            {recommendation.durationMinutes ? `${recommendation.durationMinutes} min` : 'Not supplied'}
          </dd>
        </div>
      </dl>
      <div className="mt-3">
        <p className="text-xs font-medium text-foreground">Evidence used</p>
        <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
          {recommendation.evidence.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      <div className="mt-4">
        <button
          type="button"
          className="inline-flex items-center gap-1 text-sm font-medium text-primary outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          Why this recommendation?
          <ChevronDown className={`h-4 w-4 transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
        {open && (
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
            {recommendation.why.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )}
      </div>
      <div className="mt-5 flex flex-wrap gap-2">
        {recommendation.practiceId && (
          <Button type="button" onClick={onStartPractice}>
            <Play className="h-4 w-4" />
            Start practice
          </Button>
        )}
        {material && (
          <Button type="button" variant="outline" onClick={onViewMaterial}>
            <BookOpen className="h-4 w-4" />
            View learning material
          </Button>
        )}
      </div>
    </section>
  )
}

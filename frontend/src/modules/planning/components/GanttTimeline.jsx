import { useState } from 'react'

const STATUS_DOT = {
  Todo: 'bg-muted-foreground/50',
  'In Progress': 'bg-primary',
  Blocked: 'bg-destructive',
  Done: 'bg-emerald-500',
}

function dayLabel(iso) {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

// Read-only "Gantt-lite" — a milestone timeline. We only track a due date per
// task (not a start date), so each task renders as a positioned marker along
// the sprint window rather than a start-to-end bar.
export default function GanttTimeline({ tasks, sprintStart, sprintEnd }) {
  const start = new Date(sprintStart).getTime()
  const end = new Date(sprintEnd).getTime()
  const span = Math.max(end - start, 1)
  const [today] = useState(() => Date.now())
  const todayPercent = Math.min(100, Math.max(0, ((today - start) / span) * 100))

  const sorted = [...tasks].filter((t) => t.dueDate).sort((a, b) => new Date(a.dueDate) - new Date(b.dueDate))

  if (sorted.length === 0) {
    return <p className="text-xs text-muted-foreground">No scheduled tasks yet.</p>
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[10px] text-muted-foreground pl-36 pr-2 mb-1">
        <span>{dayLabel(sprintStart)}</span>
        <span>{dayLabel(sprintEnd)}</span>
      </div>
      <div className="space-y-1.5">
        {sorted.map((task) => {
          const percent = Math.min(100, Math.max(0, ((new Date(task.dueDate).getTime() - start) / span) * 100))
          return (
            <div key={task.id} className="flex items-center gap-2">
              <span className="w-36 shrink-0 text-xs text-foreground truncate" title={task.title}>
                {task.title}
              </span>
              <div className="relative h-5 flex-1 rounded-md bg-muted/40">
                <div className="absolute inset-y-0 w-px bg-border" style={{ left: `${todayPercent}%` }} />
                <div
                  className={`absolute top-1/2 -translate-y-1/2 h-2.5 w-2.5 rounded-full border-2 border-card ${STATUS_DOT[task.status] || 'bg-muted-foreground/50'}`}
                  style={{ left: `calc(${percent}% - 5px)` }}
                  title={`${task.id} · due ${dayLabel(task.dueDate)} · ${task.status}`}
                />
              </div>
              <span className="w-16 shrink-0 text-[10px] text-muted-foreground text-right">{dayLabel(task.dueDate)}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

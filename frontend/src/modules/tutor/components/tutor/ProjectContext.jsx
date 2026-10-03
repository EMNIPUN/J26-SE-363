import { CalendarDays, FolderKanban, ListTodo } from 'lucide-react'
import Badge from '@/shared/components/Badge.jsx'
import ContextSection from '../layout/ContextSection.jsx'
import QueryState from '../common/QueryState.jsx'
import LoadingState from '../common/LoadingState.jsx'
import { useTutorContext } from '../../hooks/useTutorOverview.js'
import { formatDateRange, formatShortDate } from '../../utils/format.js'
import { PROJECT_RELEVANCE, TASK_PRIORITY, TASK_STATUS, getMeta } from '../../utils/statusMeta.js'

function ContextItem({ label, value, detail }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium leading-snug text-foreground">{value}</dd>
      {detail && <dd className="mt-0.5 text-xs text-muted-foreground">{detail}</dd>}
    </div>
  )
}

function CurrentTask({ task }) {
  const status = getMeta(TASK_STATUS, task.status)
  const priority = getMeta(TASK_PRIORITY, task.priority)
  const relevance = getMeta(PROJECT_RELEVANCE, task.projectRelevance)

  return (
    <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Current task</p>
        <Badge tone={status.tone}>{status.label}</Badge>
      </div>
      <p className="mt-1 text-sm font-semibold leading-snug text-foreground">{task.title}</p>
      {task.description && (
        <p className="mt-1 line-clamp-3 text-xs leading-relaxed text-muted-foreground">{task.description}</p>
      )}
      <dl className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs">
        <div className="flex items-center gap-1.5">
          <dt className="text-muted-foreground">Priority</dt>
          <dd>
            <Badge tone={priority.tone}>{priority.label}</Badge>
          </dd>
        </div>
        <div className="flex items-center gap-1.5">
          <dt className="text-muted-foreground">Project relevance</dt>
          <dd>
            <Badge tone={relevance.tone}>{relevance.label}</Badge>
          </dd>
        </div>
        {task.dueDate && (
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <dt>
              <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="sr-only">Due date</span>
            </dt>
            <dd>Due {formatShortDate(task.dueDate)}</dd>
          </div>
        )}
      </dl>
    </div>
  )
}

export default function ProjectContext() {
  const contextQuery = useTutorContext()

  return (
    <ContextSection icon={FolderKanban} title="Project Context" description="What you are working on right now">
      <QueryState
        query={contextQuery}
        isEmpty={(data) => !data?.task}
        loading={<LoadingState rows={3} label="Loading project context" />}
        errorTitle="Could not load your project context"
        emptyIcon={ListTodo}
        emptyTitle="No active task"
        emptyDescription="When a sprint task is assigned to you, the Tutor will tailor its support to it."
      >
        {({ project, sprint, task }) => (
          <div className="space-y-3">
            <dl className="grid grid-cols-2 gap-3">
              <ContextItem label="Project" value={project.name} />
              <ContextItem
                label={`Sprint ${sprint.number}`}
                value={sprint.name}
                detail={formatDateRange(sprint.startDate, sprint.endDate)}
              />
            </dl>
            <CurrentTask task={task} />
          </div>
        )}
      </QueryState>
    </ContextSection>
  )
}

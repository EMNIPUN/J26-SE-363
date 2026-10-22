import { useState } from 'react'
import { Check } from 'lucide-react'
import { PP1_SPRINT_CONTEXT, tasksAssignedToStudent } from '../data/pp1SprintContext.js'

function isDone(status) {
  return status === 'done' || status === 'completed'
}

function statusMeta(status) {
  if (isDone(status)) {
    return {
      label: 'Completed',
      note: 'This task is complete.',
      dot: 'bg-emerald-600 dark:bg-emerald-400',
    }
  }
  if (status === 'in_progress') {
    return {
      label: 'In progress',
      note: 'This is the task to work on now.',
      dot: 'bg-primary',
    }
  }
  return {
    label: 'Up next',
    note: 'Start this after the task that is in progress.',
    dot: 'bg-muted-foreground/45',
  }
}

function priorityLabel(priority) {
  if (priority === 'high') return 'High'
  if (priority === 'low') return 'Low'
  return 'Medium'
}

export default function StudentSprintTaskBoard() {
  const myTasks = tasksAssignedToStudent()
  const peerTasks = PP1_SPRINT_CONTEXT.tasks.filter((task) => !task.assignedToYou)
  const rows = [
    ...myTasks.map((task) => ({ task, owner: 'you' })),
    ...peerTasks.map((task) => ({ task, owner: 'team' })),
  ]
  const preferredId =
    myTasks.find((task) => task.status === 'in_progress')?.task_id ||
    myTasks.find((task) => !isDone(task.status))?.task_id ||
    myTasks[0]?.task_id ||
    rows[0]?.task.task_id ||
    null

  const [selectedId, setSelectedId] = useState(preferredId)
  const selectedRow = rows.find((row) => row.task.task_id === selectedId) || rows[0] || null
  const selected = selectedRow?.task || null
  const selectedIndex = selected ? rows.findIndex((row) => row.task.task_id === selected.task_id) : -1
  const doneCount = myTasks.filter((task) => isDone(task.status)).length
  const progress = myTasks.length ? Math.round((doneCount / myTasks.length) * 100) : 0
  const status = selected ? statusMeta(selected.status) : null

  function selectTask(taskId) {
    setSelectedId(taskId)
    if (window.matchMedia('(max-width: 767px)').matches) {
      document.getElementById('sprint-task-detail')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }

  function onListKeyDown(event) {
    if (!rows.length || !selected) return
    const current = rows.findIndex((row) => row.task.task_id === selected.task_id)
    let next = current
    if (event.key === 'ArrowDown') next = Math.min(rows.length - 1, current + 1)
    else if (event.key === 'ArrowUp') next = Math.max(0, current - 1)
    else if (event.key === 'Home') next = 0
    else if (event.key === 'End') next = rows.length - 1
    else return

    event.preventDefault()
    const taskId = rows[next].task.task_id
    setSelectedId(taskId)
    document.getElementById(`sprint-task-${taskId}`)?.focus()
  }

  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <h4 className="text-sm font-semibold tracking-tight text-foreground">
          {myTasks.length} task{myTasks.length === 1 ? '' : 's'} assigned to you
        </h4>
        <p className="text-xs text-muted-foreground">
          {doneCount} of {myTasks.length} complete
        </p>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        <span className="font-medium text-foreground">{PP1_SPRINT_CONTEXT.projectName}</span>
        <span className="px-1.5 text-border">/</span>
        {PP1_SPRINT_CONTEXT.sprintName}
      </p>
      <div
        className="mt-3 h-1 overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Assigned tasks complete"
      >
        <div className="h-full bg-primary" style={{ width: `${progress}%` }} />
      </div>
      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
        <span className="font-medium text-foreground">Sprint goal. </span>
        {PP1_SPRINT_CONTEXT.sprintGoal}
      </p>

      <div className="mt-4 overflow-hidden rounded-lg border border-border bg-card md:grid md:min-h-[22rem] md:grid-cols-[minmax(220px,280px)_minmax(0,1fr)]">
        <div
          className="border-b border-border md:border-r md:border-b-0"
          role="listbox"
          aria-label="Sprint tasks"
          onKeyDown={onListKeyDown}
        >
          <p className="border-b border-border px-3 py-2 text-xs font-medium text-muted-foreground">
            Your tasks
          </p>
          {myTasks.length === 0 ? (
            <p className="px-3 py-6 text-sm text-muted-foreground">No tasks assigned yet.</p>
          ) : (
            <ul className="divide-y divide-border">
              {myTasks.map((task, index) => (
                <TaskListItem
                  key={task.task_id}
                  task={task}
                  index={index}
                  selected={selected?.task_id === task.task_id}
                  onSelect={selectTask}
                />
              ))}
            </ul>
          )}

          {peerTasks.length > 0 ? (
            <>
              <p className="border-y border-border px-3 py-2 text-xs font-medium text-muted-foreground">
                Teammates
              </p>
              <ul className="divide-y divide-border">
                {peerTasks.map((task, index) => (
                  <TaskListItem
                    key={task.task_id}
                    task={task}
                    index={myTasks.length + index}
                    selected={selected?.task_id === task.task_id}
                    onSelect={selectTask}
                    teammate
                  />
                ))}
              </ul>
            </>
          ) : null}
        </div>

        <section
          id="sprint-task-detail"
          className="min-w-0"
          aria-live="polite"
          aria-label={selected ? `${selected.title} details` : 'Task details'}
        >
          {selected && status ? (
            <>
              <header className="border-b border-border px-4 py-4 sm:px-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs text-muted-foreground">
                      Task {selectedIndex + 1} of {rows.length}
                      {selectedRow.owner === 'team' ? ' · Teammate' : ''}
                    </p>
                    <h5 className="mt-1 text-base font-semibold tracking-tight text-foreground">
                      {selected.title}
                    </h5>
                  </div>
                  <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2 py-1 text-xs font-medium text-foreground">
                    <span className={`h-1.5 w-1.5 rounded-full ${status.dot}`} aria-hidden="true" />
                    {status.label}
                  </span>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">{status.note}</p>
              </header>

              <div className="px-4 py-4 sm:px-5">
                <dl className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <dt className="text-xs text-muted-foreground">Priority</dt>
                    <dd className="mt-1 font-medium text-foreground">{priorityLabel(selected.priority)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Owner</dt>
                    <dd className="mt-1 font-medium text-foreground">
                      {selectedRow.owner === 'team' ? 'Teammate' : 'You'}
                    </dd>
                  </div>
                </dl>

                <p className="mt-4 text-sm leading-relaxed text-foreground/90">{selected.description}</p>

                <h6 className="mt-5 text-xs font-medium text-muted-foreground">Acceptance criteria</h6>
                <ul className="mt-2 divide-y divide-border border-y border-border">
                  {selected.acceptance_criteria.map((item) => {
                    const complete = isDone(selected.status)
                    return (
                      <li key={item} className="flex items-start gap-2.5 py-2.5 text-sm text-foreground">
                        <span
                          className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-[3px] border ${
                            complete
                              ? 'border-emerald-700/40 text-emerald-700 dark:border-emerald-400/40 dark:text-emerald-400'
                              : 'border-border text-transparent'
                          }`}
                          aria-hidden="true"
                        >
                          {complete ? <Check className="h-3 w-3" strokeWidth={2.5} /> : null}
                        </span>
                        <span>{item}</span>
                      </li>
                    )
                  })}
                </ul>
                <p className="mt-3 font-mono text-[11px] text-muted-foreground">{selected.task_id}</p>
              </div>
            </>
          ) : (
            <p className="px-5 py-8 text-sm text-muted-foreground">
              Select a task to see its description and acceptance criteria.
            </p>
          )}
        </section>
      </div>
    </div>
  )
}

function TaskListItem({ task, index, selected, onSelect, teammate = false }) {
  const status = statusMeta(task.status)

  return (
    <li>
      <button
        id={`sprint-task-${task.task_id}`}
        type="button"
        role="option"
        aria-selected={selected}
        tabIndex={selected ? 0 : -1}
        onClick={() => onSelect(task.task_id)}
        className={`flex w-full gap-3 px-3 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset ${
          selected ? 'bg-accent shadow-[inset_2px_0_0_0_var(--primary)]' : 'hover:bg-muted/70'
        }`}
      >
        <span className="w-4 shrink-0 pt-0.5 text-xs tabular-nums text-muted-foreground">{index + 1}</span>
        <span className="min-w-0">
          <span className="block text-sm font-medium leading-snug text-foreground">{task.title}</span>
          <span className="mt-1 flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
            <span className={`h-1.5 w-1.5 rounded-full ${status.dot}`} aria-hidden="true" />
            <span>{status.label}</span>
            <span aria-hidden="true">·</span>
            <span>{teammate ? 'Teammate' : priorityLabel(task.priority)}</span>
          </span>
        </span>
      </button>
    </li>
  )
}

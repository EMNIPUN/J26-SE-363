import { Fragment, useMemo } from 'react'
import PropTypes from 'prop-types'
import { Check, CircleAlert, Hourglass, Loader2 } from 'lucide-react'
import { duration } from './format.js'
import { laneRows, lastLine, nodeStates, pathOf, rfSummary, rowState, studentsIn, teamSteps } from './pipelineModel.js'
import './pipeline.css'

const DESCRIPTION = {
  load_run_context: 'Reads the team, its repository and the students',
  prepare_workspace: 'Makes a read-only copy of the repository',
  collect_scrum: 'Reads the sprint and its tasks from the Scrum board',
  collect_github: 'Reads pull requests, reviews and comments',
  build_team_evidence: 'Turns commits, tasks and reviews into evidence for each student',
  evidence_quality_gate: 'Checks that authors can be matched to students',
  dispatch_students: 'Assesses every student, several at a time',
  team_cross_check: 'Looks for problems across the team',
  team_report: 'Writes the report for the lecturer',
  publish: 'Saves the results',
  student_evidence_check: "Looks at the student's evidence",
  factor_effort: 'How much real work',
  factor_consistency: 'How steadily',
  factor_collaboration: 'Reviews and discussion',
  factor_task_complexity: 'How demanding the tasks',
  rf_subagent: 'Does the code meet the tasks',
  join_factors: 'Collects the factor results',
  factor_audit: 'Checks the results and re-runs a failed factor',
  ownership_quiz: 'The question about their own code',
  behavioral_pattern: 'The working pattern',
  fusion: 'Combines the factors into a mark',
  explain: 'Investigates doubts and writes the reasons',
  export: 'Saves the result',
}

function Marker({ state }) {
  if (state === 'done') return <Check className="h-4 w-4" aria-hidden="true" />
  if (state === 'failed') return <CircleAlert className="h-4 w-4" aria-hidden="true" />
  if (state === 'waiting') return <Hourglass className="h-4 w-4" aria-hidden="true" />
  if (state === 'active') return <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
  return <span className="h-1.5 w-1.5 rounded-full bg-current opacity-50" />
}
Marker.propTypes = { state: PropTypes.string }

const LABEL = { idle: 'Waiting', active: 'Running', done: 'Done', failed: 'Failed', waiting: 'Waiting for you' }
const labelOf = (n) => n.label

function Caption({ state, seconds, line, fallback }) {
  return (
    <>
      <span className="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
        <span className={state === 'failed' ? 'font-medium text-rose-600' : state === 'active' ? 'font-medium text-primary' : ''}>{LABEL[state]}</span>
        {seconds != null && state === 'done' && <span>{duration(seconds)}</span>}
      </span>
      <span className="mt-0.5 block truncate text-xs text-muted-foreground">{line || fallback}</span>
    </>
  )
}
Caption.propTypes = { state: PropTypes.string, seconds: PropTypes.number, line: PropTypes.string, fallback: PropTypes.string }

function Step({ state, last, linkState, children }) {
  return (
    <div className={`pf-step ${state}`}>
      <div className="pf-rail">
        <span className="pf-marker"><Marker state={state} /></span>
        {!last && <span className={`pf-line ${linkState}`} />}
      </div>
      <div className="min-w-0">{children}</div>
    </div>
  )
}
Step.propTypes = { state: PropTypes.string, last: PropTypes.bool, linkState: PropTypes.string, children: PropTypes.node }

/** The line below a step: lit while the step above is done and the one below is running, green once both are done. */
function link(current, next) {
  if (current === 'done' && (next === 'active' || next === 'waiting')) return 'flowing'
  if (current === 'done' && next === 'done') return 'done'
  if (next === 'failed') return 'failed'
  return 'idle'
}

function RfBody({ events, student }) {
  const s = useMemo(() => rfSummary(events, student), [events, student])
  if (!s.tasks.length && !s.calls) return null
  return (
    <div className="mt-2 rounded-lg bg-muted/60 p-2 text-xs">
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground">
        <span>{s.calls} model calls</span><span>{s.tokens.toLocaleString()} tokens</span>{s.errors > 0 && <span className="text-amber-600">{s.errors} refused and retried</span>}
      </div>
      <ul className="mt-1 grid gap-0.5">
        {s.tasks.map((t) => (
          <li key={t.id} className="flex items-center justify-between gap-2">
            <span className="truncate font-mono">{t.id}</span>
            <span className="text-muted-foreground">{t.state === 'done' ? `${Math.round(t.fulfilment * 100)}% of the criteria` : t.state === 'judging' ? 'judging...' : t.state === 'skipped' ? 'nothing to show' : 'not judged'}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
RfBody.propTypes = { events: PropTypes.array, student: PropTypes.string }

function Lane({ topology, events, states, student, selected, onSelect }) {
  const rows = useMemo(() => laneRows(topology), [topology])
  const states2 = rows.map((r) => rowState(r, states, student))
  return (
    <div className="pf-lane">
      {rows.map((row, i) => {
        const st = states2[i]
        const last = i === rows.length - 1
        const next = states2[i + 1]
        if (row.length > 1) {
          return (
            <Step key={row[0].id} state={st} last={last} linkState={link(st, next)}>
              <div className="pf-parallel">
                {row.map((n) => {
                  const path = pathOf(n, student)
                  const ns = states[path]?.state || 'idle'
                  return (
                    <button key={n.id} type="button" onClick={() => onSelect(path)} className={`pf-chip ${ns} ${n.id === 'rf_subagent' ? 'wide' : ''} ${selected === path ? 'selected' : ''}`} aria-label={`${labelOf(n)}: ${LABEL[ns]}`}>
                      <span className="flex items-center justify-between gap-2 text-sm font-medium text-foreground"><span className="truncate">{labelOf(n)}</span><Marker state={ns} /></span>
                      <Caption state={ns} seconds={states[path]?.seconds} line={lastLine(events, path)} fallback={DESCRIPTION[n.id]} />
                      {n.id === 'rf_subagent' && ns !== 'idle' && <RfBody events={events} student={student} />}
                    </button>
                  )
                })}
              </div>
            </Step>
          )
        }
        const n = row[0]
        const path = pathOf(n, student)
        return (
          <Step key={n.id} state={st} last={last} linkState={link(st, next)}>
            <button type="button" onClick={() => onSelect(path)} className={`pf-card ${selected === path ? 'selected' : ''}`} style={{ marginBottom: 10 }} aria-label={`${labelOf(n)}: ${LABEL[st]}`}>
              <span className="block text-sm font-medium text-foreground">{labelOf(n)}</span>
              <Caption state={st} seconds={states[path]?.seconds} line={lastLine(events, path)} fallback={DESCRIPTION[n.id]} />
            </button>
          </Step>
        )
      })}
    </div>
  )
}
Lane.propTypes = { topology: PropTypes.object, events: PropTypes.array, states: PropTypes.object, student: PropTypes.string, selected: PropTypes.string, onSelect: PropTypes.func, names: PropTypes.object }

/**
 * The run as one vertical flow. The team's steps run down the page; the "Assess students" step opens one student's lane (pick the student above it).
 * `events` are the events up to now (a live run) or up to the point of the replay slider (a finished run).
 */
export default function PipelineFlow({ topology, events, student, onStudent, selected, onSelect, names }) {
  const states = useMemo(() => nodeStates(events), [events])
  const students = useMemo(() => studentsIn(events), [events])
  const steps = useMemo(() => teamSteps(topology), [topology])
  // show the student who is being worked on now (the first one not finished), until the lecturer picks another
  const lane = student || (students.find((s) => s.state === 'active') || students[0])?.id || null
  const stateOf = (n) => states[pathOf(n, null)]?.state || 'idle'
  return (
    <div className="pf-flow">
      {steps.map((n, i) => {
        const st = stateOf(n)
        const path = pathOf(n, null)
        const next = i < steps.length - 1 ? stateOf(steps[i + 1]) : 'idle'
        return (
          <Step key={n.id} state={st} last={i === steps.length - 1} linkState={link(st, next)}>
            <button type="button" onClick={() => onSelect(path)} className={`pf-card ${selected === path ? 'selected' : ''}`} aria-label={`${labelOf(n)}: ${LABEL[st]}`}>
              <span className="block text-sm font-semibold text-foreground">{labelOf(n)}</span>
              <Caption state={st} seconds={states[path]?.seconds} line={lastLine(events, path)} fallback={DESCRIPTION[n.id]} />
            </button>
            {n.id === 'dispatch_students' && students.length > 0 && (
              <div className="-mt-2 mb-3 flex flex-wrap items-center gap-1.5" role="tablist" aria-label="Student">
                {students.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    role="tab"
                    aria-selected={lane === s.id}
                    onClick={() => onStudent(s.id)}
                    className={`rounded-full border px-2.5 py-1 text-xs transition-colors ${lane === s.id ? 'border-primary bg-primary text-primary-foreground' : 'bg-background hover:border-primary/50'}`}
                  >
                    {names?.[s.id] || s.id.slice(0, 8)}{s.state === 'done' ? ' ✓' : s.state === 'failed' ? ' !' : ''}
                  </button>
                ))}
              </div>
            )}
            {n.id === 'dispatch_students' && lane && (
              <Fragment>
                <Lane topology={topology} events={events} states={states} student={lane} selected={selected} onSelect={onSelect} />
              </Fragment>
            )}
          </Step>
        )
      })}
    </div>
  )
}
PipelineFlow.propTypes = { topology: PropTypes.object.isRequired, events: PropTypes.array.isRequired, student: PropTypes.string, onStudent: PropTypes.func, selected: PropTypes.string, onSelect: PropTypes.func, names: PropTypes.object }

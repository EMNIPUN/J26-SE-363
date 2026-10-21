import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import PropTypes from 'prop-types'
import { BrainCircuit, Check, ChevronDown, ChevronRight, CircleAlert, Hourglass, Loader2, Terminal } from 'lucide-react'
import { duration } from './format.js'
import { scrollerOf } from './useContainerWidth.js'
import { laneRows, lastLine, llmSummary, nodeStates, pathOf, producedFields, rfSummary, rowState, studentsIn, teamSteps } from './pipelineModel.js'
import './pipeline.css'

function Marker({ state }) {
  if (state === 'done') return <Check className="h-3 w-3" aria-hidden="true" />
  if (state === 'failed') return <CircleAlert className="h-3 w-3" aria-hidden="true" />
  if (state === 'waiting') return <Hourglass className="h-3 w-3" aria-hidden="true" />
  if (state === 'active') return <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
  return <span className="h-1.5 w-1.5 rounded-full bg-current opacity-50" />
}
Marker.propTypes = { state: PropTypes.string }

const LABEL = { idle: 'Waiting', active: 'Running', done: 'Done', failed: 'Failed', waiting: 'Waiting for you' }
const labelOf = (n) => n.label

function Caption({ state, seconds, line, fallback, model }) {
  return (
    <>
      <span className="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
        <span className={state === 'failed' ? 'font-medium text-rose-600' : state === 'active' ? 'font-medium text-primary' : ''}>{LABEL[state]}</span>
        {seconds != null && state === 'done' && <span>{duration(seconds)}</span>}
      </span>
      <span className="mt-0.5 block truncate text-xs text-muted-foreground">{line || fallback}</span>
      {model?.calls > 0 && <span className="block text-[11px] text-muted-foreground">{model.calls} model calls · {model.tokens.toLocaleString()} tokens</span>}
    </>
  )
}
Caption.propTypes = { state: PropTypes.string, seconds: PropTypes.number, line: PropTypes.string, fallback: PropTypes.string, model: PropTypes.object }

function Produces({ node, events, path }) {
  if (!node?.produces?.length) return null
  const produced = producedFields(events, path)
  return (
    <div className="mt-1 flex flex-wrap gap-1" aria-label="Produces">
      {node.produces.map((field) => {
        const mark = produced[field]
        return <span key={field} className={`rounded border px-1.5 py-0.5 text-[10px] ${mark?.fallback ? 'border-amber-500/40 text-amber-700 dark:text-amber-400' : 'text-muted-foreground'}`}>{field.replace(/_/g, ' ')}{mark?.verified ? ' · verified' : mark?.fallback ? ' · fallback' : ''}</span>
      })}
    </div>
  )
}
Produces.propTypes = { node: PropTypes.object, events: PropTypes.array, path: PropTypes.string }

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

function RfSubagentSection({ node, topology, events, states, student, selected, onSelect, nodeState }) {
  const [expanded, setExpanded] = useState(true)
  const path = pathOf(node, student)
  const subGraphRef = useRef(null)
  const logBoxRef = useRef(null)

  const rfNodes = useMemo(() => {
    return (topology?.nodes || []).filter((n) => n.group === 'rf')
  }, [topology])

  const rfLogs = useMemo(() => {
    return events.filter((e) =>
      e.node_path === path ||
      (e.node_path && e.node_path.startsWith(`${path}/`))
    ).slice(-30)
  }, [events, path])

  const isStarted = nodeState !== 'idle'
  const lastLogSeq = rfLogs[rfLogs.length - 1]?.seq // the list keeps only the latest 30, so its length stops changing: the newest entry is what tells that there is more

  // Auto-scroll subagent graph horizontally to active subnode
  useEffect(() => {
    if (!subGraphRef.current) return
    const activeSub = subGraphRef.current.querySelector('.pf-rf-node.active')
    if (activeSub) {
      // sideways inside the sub-agent graph only; scrollIntoView would also move the page
      const box = subGraphRef.current
      box.scrollTo({ left: activeSub.offsetLeft - (box.clientWidth - activeSub.offsetWidth) / 2, behavior: 'smooth' })
    }
  }, [states])

  // Auto-scroll subagent log card down to latest logs
  useEffect(() => {
    if (logBoxRef.current) {
      logBoxRef.current.scrollTo({
        top: logBoxRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [rfLogs.length, lastLogSeq])

  return (
    <div className={`pf-chip wide ${nodeState} ${selected === path ? 'selected' : ''}`}>
      <div
        className="flex items-center justify-between gap-2 cursor-pointer select-none"
        onClick={() => onSelect(path)}
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <BrainCircuit className="h-4 w-4 text-primary" />
          <span>{labelOf(node)}</span>
          <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-normal text-muted-foreground">
            Sub-agent
          </span>
        </span>
        <div className="flex items-center gap-2">
          {isStarted && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                setExpanded(!expanded)
              }}
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-muted transition-colors"
            >
              {expanded ? (
                <>
                  <ChevronDown className="h-3.5 w-3.5" />
                  <span>Hide steps</span>
                </>
              ) : (
                <>
                  <ChevronRight className="h-3.5 w-3.5" />
                  <span>Show steps</span>
                </>
              )}
            </button>
          )}
          <Marker state={nodeState} />
        </div>
      </div>

      <Caption
        state={nodeState}
        seconds={states[path]?.seconds}
        line={lastLine(events, path)}
        fallback={node.description}
        model={node.uses_model ? llmSummary(events, path) : null}
      />
      <Produces node={node} events={events} path={path} />

      {isStarted && expanded && (
        <div className="pf-rf-container">
          <div className="pf-rf-toolbar">
            <span className="text-[11px] font-medium text-muted-foreground flex items-center gap-1.5">
              <span>Steps</span>
            </span>
          </div>

          <div ref={subGraphRef} className="pf-rf-graph">
            {rfNodes.map((rn, idx) => {
              const subPath = `${path}/${rn.id}`
              const subState = states[subPath]?.state || 'idle'
              const isSubSelected = selected === subPath
              return (
                <Fragment key={rn.id}>
                  <div
                    onClick={(e) => {
                      e.stopPropagation()
                      onSelect(subPath)
                    }}
                    className={`pf-rf-node ${subState} ${isSubSelected ? 'selected' : ''}`}
                    title={rn.id}
                  >
                    <Marker state={subState} />
                    <span>{rn.label || rn.id.replace(/_/g, ' ')}</span>
                    {states[subPath]?.seconds != null && (
                      <span className="text-[10px] text-muted-foreground tabular-nums">
                        {states[subPath].seconds}s
                      </span>
                    )}
                  </div>
                  {idx < rfNodes.length - 1 && (
                    <span className="pf-rf-arrow">→</span>
                  )}
                </Fragment>
              )
            })}
          </div>

          {rfLogs.length > 0 && (
            <div className="mt-2">
              <div className="flex items-center justify-between text-[11px] text-muted-foreground mb-1">
                <span className="font-medium flex items-center gap-1">
                  <Terminal className="h-3 w-3" />
                  Activity log
                </span>
                <span className="text-[10px]">{rfLogs.length} entries</span>
              </div>
              <div ref={logBoxRef} className="pf-rf-log-card">
                {rfLogs.map((e, index) => {
                  const nodeTag = e.node_path?.split('/').pop() || 'rf'
                  return (
                    <div key={e.seq ?? index} className="pf-rf-log-item">
                      <span className="text-muted-foreground shrink-0 text-[10px]">
                        {e.ts ? String(e.ts).slice(11, 19) : ''}
                      </span>
                      <span className="shrink-0 rounded bg-muted px-1 text-[10px] text-muted-foreground">
                        {nodeTag.replace(/_/g, ' ')}
                      </span>
                      <span className={`break-all ${e.level === 'warn' ? 'text-amber-500' : e.level === 'error' ? 'text-rose-500' : 'text-foreground'}`}>
                        {e.message || (e.type === 'node_start' ? `Started ${nodeTag}` : e.type === 'node_end' ? `Finished ${nodeTag}` : '')}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <RfBody events={events} student={student} />
        </div>
      )}
    </div>
  )
}
RfSubagentSection.propTypes = {
  node: PropTypes.object.isRequired,
  topology: PropTypes.object.isRequired,
  events: PropTypes.array.isRequired,
  states: PropTypes.object.isRequired,
  student: PropTypes.string.isRequired,
  selected: PropTypes.string,
  onSelect: PropTypes.func.isRequired,
  nodeState: PropTypes.string.isRequired,
}

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
                  if (n.id === 'rf_subagent') {
                    return (
                      <RfSubagentSection
                        key={n.id}
                        node={n}
                        topology={topology}
                        events={events}
                        states={states}
                        student={student}
                        selected={selected}
                        onSelect={onSelect}
                        nodeState={ns}
                      />
                    )
                  }
                  return (
                    <button key={n.id} type="button" onClick={() => onSelect(path)} className={`pf-chip ${ns} ${selected === path ? 'selected' : ''}`} aria-label={`${labelOf(n)}: ${LABEL[ns]}`}>
                      <span className="flex items-center justify-between gap-2 text-sm font-medium text-foreground"><span className="truncate">{labelOf(n)}</span><Marker state={ns} /></span>
                      <Caption state={ns} seconds={states[path]?.seconds} line={lastLine(events, path)} fallback={n.description} model={n.uses_model ? llmSummary(events, path) : null} />
                      <Produces node={n} events={events} path={path} />
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
              <Caption state={st} seconds={states[path]?.seconds} line={lastLine(events, path)} fallback={n.description} model={n.uses_model ? llmSummary(events, path) : null} />
              <Produces node={n} events={events} path={path} />
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
  const containerRef = useRef(null)
  const lastActiveRef = useRef(null)
  const states = useMemo(() => nodeStates(events), [events])
  const students = useMemo(() => studentsIn(events), [events])
  const steps = useMemo(() => teamSteps(topology), [topology])
  // show the student who is being worked on now (the first one not finished), until the lecturer picks another
  const lane = student || (students.find((s) => s.state === 'active') || students[0])?.id || null
  const stateOf = (n) => states[pathOf(n, null)]?.state || 'idle'

  // Auto-scroll pipeline vertically to whichever node is executing
  useEffect(() => {
    if (!containerRef.current) return
    const activeEl = containerRef.current.querySelector(
      '.pf-rf-node.active, .pf-chip.active, .pf-card.active, .pf-step.active'
    )
    if (activeEl && activeEl !== lastActiveRef.current) {
      lastActiveRef.current = activeEl
      // scroll the pipeline pane only: scrollIntoView would also move the page and the logs panel with it
      const pane = scrollerOf(containerRef.current)
      if (pane && pane.scrollHeight > pane.clientHeight) {
        const box = pane.getBoundingClientRect()
        const at = activeEl.getBoundingClientRect()
        pane.scrollTo({ top: pane.scrollTop + (at.top - box.top) - (box.height - at.height) / 2, behavior: 'smooth' })  // the running step is kept in the middle of the pane
      } else {
        activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' })
      }
    }
  }, [events.length, states])

  return (
    <div ref={containerRef} className="pf-flow">
      {steps.map((n, i) => {
        const st = stateOf(n)
        const path = pathOf(n, null)
        const next = i < steps.length - 1 ? stateOf(steps[i + 1]) : 'idle'
        return (
          <Step key={n.id} state={st} last={i === steps.length - 1} linkState={link(st, next)}>
            <button type="button" onClick={() => onSelect(path)} className={`pf-card ${selected === path ? 'selected' : ''}`} aria-label={`${labelOf(n)}: ${LABEL[st]}`}>
              <span className="block text-sm font-semibold text-foreground">{labelOf(n)}</span>
              <Caption state={st} seconds={states[path]?.seconds} line={lastLine(events, path)} fallback={n.description} model={n.uses_model ? llmSummary(events, path) : null} />
              <Produces node={n} events={events} path={path} />
            </button>
            {n.id === 'dispatch_students' && students.length > 0 && (
              <div className="-mt-1 mb-3 inline-flex max-w-full flex-wrap items-center gap-0.5 rounded-lg bg-muted p-0.5" role="tablist" aria-label="Student">
                {students.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    role="tab"
                    aria-selected={lane === s.id}
                    onClick={() => onStudent(s.id)}
                    className={`rounded-md px-2.5 py-1 text-xs transition-colors ${lane === s.id ? 'bg-card font-medium text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
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

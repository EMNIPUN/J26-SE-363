import { useMemo } from 'react'
import { Check, CircleAlert, Hourglass } from 'lucide-react'
import { edgePath, edgeState, layout, NODE_H, NODE_W, pathOf } from './pipelineModel.js'
import './pipeline.css'

function Panel({ title, nodes, edges, states, student, selected, onSelect, extra }) {
  const { pos, width, height } = useMemo(() => layout(nodes, edges), [nodes, edges])
  const stateOf = (n) => states[pathOf(n, student)]
  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        {extra}
      </div>
      <div className="pl-panel">
        <div className="pl-stage" style={{ width, height }}>
          <svg className="pl-svg" width={width} height={height} aria-hidden="true">
            {edges.map((e) => {
              const a = nodes.find((n) => n.id === e.from)
              const b = nodes.find((n) => n.id === e.to)
              if (!a || !b) return null
              const d = edgePath(pos[a.id], pos[b.id])
              const st = edgeState(stateOf(a), stateOf(b))
              const id = `edge-${student || 'team'}-${a.id}-${b.id}`
              return (
                <g key={id}>
                  <path id={id} d={d} className={`pl-edge ${st}`} />
                  {st === 'flowing' && (
                    <>
                      <path d={d} className="pl-edge-glow" />
                      <circle r="5" className="pl-comet">
                        <animateMotion dur="1.3s" repeatCount="indefinite"><mpath href={`#${id}`} /></animateMotion>
                      </circle>
                    </>
                  )}
                </g>
              )
            })}
          </svg>
          {nodes.map((n) => {
            const s = stateOf(n)
            const state = s?.state || 'idle'
            const path = pathOf(n, student)
            return (
              <button key={n.id} type="button" className={`pl-node ${state} ${selected === path ? 'selected' : ''}`} style={{ left: pos[n.id].x, top: pos[n.id].y, width: NODE_W, height: NODE_H }}
                onClick={() => onSelect(path, n)} aria-label={`${n.label}: ${state}`}>
                <span className="flex items-center gap-1.5 font-medium">
                  {state === 'done' && <Check className="h-3.5 w-3.5 text-emerald-600" />}
                  {state === 'failed' && <CircleAlert className="h-3.5 w-3.5 text-destructive" />}
                  {state === 'waiting' && <Hourglass className="h-3.5 w-3.5 text-amber-600" />}
                  <span className="truncate">{n.label}</span>
                </span>
                <small>{state === 'idle' ? '' : state === 'active' ? 'running' : s?.seconds != null ? `${state} · ${s.seconds}s` : state}</small>
              </button>
            )
          })}
        </div>
      </div>
    </section>
  )
}

/** The team graph, one student's lane and, once that student's sub-agent has started, the Requirement Fulfillment sub-agent. */
export default function PipelineCanvas({ topology, states, student, selected, onSelect, studentPicker }) {
  const parts = useMemo(() => {
    const by = (g) => topology.nodes.filter((n) => n.group === g)
    const ed = (g) => topology.edges.filter((e) => e.group === g)
    return { team: [by('team'), ed('team')], student: [by('student'), ed('student')], rf: [by('rf'), ed('rf')] }
  }, [topology])
  const rfSeen = student && Object.keys(states).some((p) => p.startsWith(`student:${student}/rf_subagent`))
  return (
    <div className="space-y-5">
      <Panel title="Team run" nodes={parts.team[0]} edges={parts.team[1]} states={states} selected={selected} onSelect={onSelect} />
      {student ? (
        <Panel title={`Student ${student}`} nodes={parts.student[0]} edges={parts.student[1]} states={states} student={student} selected={selected} onSelect={onSelect} extra={studentPicker} />
      ) : (
        <p className="text-sm text-muted-foreground">Students appear here when the run reaches &ldquo;Assess students&rdquo;.</p>
      )}
      {rfSeen && (
        <Panel title="Requirement Fulfillment sub-agent" nodes={parts.rf[0]} edges={parts.rf[1]} states={states} student={student} selected={selected} onSelect={onSelect}
          extra={<span className="text-xs text-muted-foreground">Its steps are listed in the log of the Requirement Fulfillment node above.</span>} />
      )}
    </div>
  )
}

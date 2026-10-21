import { useState } from 'react'
import { Card } from '@/components/ui/card'
import { DIAGRAM_LABELS, GRAPH_TITLE, NESTED, nodeLabel, nodeStyle } from '../lib/agents.js'
import { layoutGraph } from '../lib/graphLayout.js'

const NESTED_LAYOUT = { nodeW: 132, nodeH: 34, gapX: 18, gapY: 26, pad: 10, side: 36 }
const LEGEND = ['completed', 'ran', 'partial', 'skipped', 'failed', 'not run']

function Edges({ edges, id }) {
  return (
    <g fill="none" className="stroke-muted-foreground/70" strokeWidth="1.4">
      {edges.map((e) => (
        <path key={`${e.from}>${e.to}`} d={e.d} data-edge={`${e.from}>${e.to}`} data-kind={e.kind} strokeDasharray={e.conditional ? '5 4' : undefined} markerEnd={`url(#arrow-${id})`} />
      ))}
    </g>
  )
}

function Node({ node, status, label, host, expanded, onToggle }) {
  const [classes, text] = nodeStyle(status)
  const ends = node.id === '__start__' || node.id === '__end__'
  const interactive = host && !ends
  const props = interactive
    ? { role: 'button', tabIndex: 0, 'aria-expanded': expanded, 'aria-label': `${label}: ${text}. ${expanded ? 'Hide' : 'Show'} the ${GRAPH_TITLE[host]}`, onClick: onToggle, onKeyDown: (e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onToggle()), className: 'cursor-pointer' }
    : {}
  return (
    <g data-node={node.id} data-status={ends ? undefined : status} {...props}>
      <rect x={node.x} y={node.y} width={node.w} height={node.h} rx={ends ? node.h / 2 : 8} strokeWidth="1.6" className={ends ? 'fill-muted stroke-border' : classes} />
      <text x={node.x + node.w / 2} y={node.y + (ends ? node.h / 2 + 4 : node.h / 2 - 3)} textAnchor="middle" fontSize="12" fontWeight="600" className="fill-foreground">
        {label}
      </text>
      {!ends && (
        <text x={node.x + node.w / 2} y={node.y + node.h / 2 + 11} textAnchor="middle" fontSize="10" className="fill-muted-foreground">
          {text}
          {interactive ? (expanded ? ' · ▾ hide detail' : ' · ▸ show detail') : ''}
        </text>
      )}
    </g>
  )
}

// A graph on its own: nodes coloured by status, edges (dashed when conditional, curved round the side when they loop or skip a row).
function Graph({ id, statuses, layout, labels }) {
  return (
    <g>
      <Edges edges={layout.edges} id={id} />
      {layout.nodes.map((node) => (
        <Node key={node.id} node={node} status={statuses?.[node.id]} label={nodeLabel(node.id, labels)} />
      ))}
    </g>
  )
}

// The whole workflow with the agent graphs nested under their node: click (or press Enter on) scan, interpret, trace or questions to open the graph that runs inside it.
export default function WorkflowDiagram({ workflow, initiallyExpanded = [] }) {
  const [expanded, setExpanded] = useState(() => new Set(initiallyExpanded))
  const { graphs, ran } = workflow
  const main = graphs.workflow
  if (!main?.nodes?.length) {
    return <p data-slot="diagram-missing" className="text-sm text-muted-foreground">The diagram files were not found for this run, so no diagram can be drawn.</p>
  }
  const hostOf = (id) => (NESTED[id] && graphs[NESTED[id]]?.nodes?.length ? NESTED[id] : null)
  const open = [...expanded].filter((id) => hostOf(id))
  const nestedLayouts = Object.fromEntries(open.map((id) => [id, layoutGraph(graphs[NESTED[id]].nodes, graphs[NESTED[id]].edges, NESTED_LAYOUT)]))
  const base = layoutGraph(main.nodes, main.edges)
  const rowExtra = []
  for (const id of open) {
    const level = base.nodes.find((n) => n.id === id)?.level
    if (level !== undefined) rowExtra[level] = Math.max(rowExtra[level] ?? 0, nestedLayouts[id].height + 22)
  }
  const layout = layoutGraph(main.nodes, main.edges, { rowExtra })
  const placed = Object.fromEntries(layout.nodes.map((n) => [n.id, n]))
  const nestedRight = open.map((id) => placed[id].x + placed[id].w / 2 + 28 + nestedLayouts[id].width + 16)
  const width = Math.max(layout.width, ...nestedRight)
  const toggle = (id) => setExpanded((current) => {
    const next = new Set(current)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    return next
  })

  return (
    <div data-slot="workflow-diagram" className="space-y-3">
      <svg role="img" aria-label="The Security Assistant workflow: each node is a stage, coloured by what happened to it in this run" viewBox={`0 0 ${width} ${layout.height}`} className="mx-auto h-auto w-full max-w-3xl">
        <defs>
          <marker id="arrow-main" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" className="fill-muted-foreground" />
          </marker>
          <marker id="arrow-nested" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" className="fill-muted-foreground" />
          </marker>
        </defs>
        <Edges edges={layout.edges} id="main" />
        {layout.nodes.map((node) => (
          <Node key={node.id} node={node} status={ran.workflow?.[node.id]} label={nodeLabel(node.id, DIAGRAM_LABELS)} host={hostOf(node.id)} expanded={expanded.has(node.id)} onToggle={() => toggle(node.id)} />
        ))}
        {open.map((id) => {
          const host = placed[id]
          const g = NESTED[id]
          const x = host.x + host.w / 2 + 28
          const y = host.y + host.h + 14
          return (
            <g key={id} data-nested={g} data-host={id} transform={`translate(${x} ${y})`}>
              <rect x="-8" y="-6" width={nestedLayouts[id].width + 16} height={nestedLayouts[id].height + 12} rx="10" className="fill-muted/40 stroke-border" strokeDasharray="3 3" />
              <text x="0" y="6" fontSize="10" className="fill-muted-foreground">{GRAPH_TITLE[g]} (inside {nodeLabel(id, DIAGRAM_LABELS)})</text>
              <g transform="translate(0 10)">
                <Graph id="nested" statuses={ran[g]} layout={nestedLayouts[id]} labels={DIAGRAM_LABELS} />
              </g>
            </g>
          )
        })}
      </svg>

      <ul data-slot="legend" className="flex flex-wrap items-center justify-center gap-3 text-xs text-muted-foreground">
        {LEGEND.map((status) => (
          <li key={status} className="flex items-center gap-1.5">
            <svg width="22" height="12" aria-hidden="true"><rect x="1" y="1" width="20" height="10" rx="3" strokeWidth="1.5" className={nodeStyle(status)[0]} /></svg>
            {status}
          </li>
        ))}
        <li>dashed arrow: conditional edge</li>
      </ul>

      <details data-slot="mermaid-source" className="text-xs">
        <summary className="cursor-pointer text-muted-foreground">Mermaid source of the diagrams (generated from the code, docs/*.mmd)</summary>
        {Object.entries(graphs).map(([name, g]) => (
          <div key={name} className="mt-2">
            <p className="font-semibold">{GRAPH_TITLE[name] ?? name}</p>
            <pre className="overflow-x-auto rounded-lg border border-border bg-muted/40 p-2 font-mono">{g.mmd ?? 'not available'}</pre>
          </div>
        ))}
      </details>
    </div>
  )
}

export function DiagramCard(props) {
  return (
    <Card data-slot="workflow-card" className="gap-3 p-5">
      <div>
        <h2 className="text-sm font-semibold">Workflow diagram</h2>
        <p className="text-xs text-muted-foreground">Generated from the code. A node&apos;s colour is what happened to it in this run; open a node with a ▸ to see the agent graph that runs inside it.</p>
      </div>
      <WorkflowDiagram {...props} />
    </Card>
  )
}

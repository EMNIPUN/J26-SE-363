/**
 * Pure logic of the live pipeline view: where each node sits, and what state each node and edge is in.
 *
 * The graph comes from the Core API (GET /performance/graph), the state from the run's events:
 *   node_start -> active, node_end -> done, node_error -> failed, node_wait -> waiting.
 * An event's node_path is `team/<node>` or `student:<ID>/<node>`.
 */

export const NODE_W = 168
export const NODE_H = 46
const GAP_X = 52
const GAP_Y = 18

/** Layers of a directed graph: the longest path from a source, ignoring edges that go back (loops such as act -> decide). */
export function layers(nodeIds, edges) {
  const out = new Map(nodeIds.map((n) => [n, []]))
  const indeg = new Map(nodeIds.map((n) => [n, 0]))
  for (const e of edges) {
    if (out.has(e.from) && out.has(e.to)) out.get(e.from).push(e.to)
  }
  // drop back edges found by a depth-first search
  const state = new Map()
  const forward = []
  const visit = (n) => {
    state.set(n, 1)
    for (const m of out.get(n)) {
      if (state.get(m) === 1) continue
      forward.push([n, m])
      if (!state.has(m)) visit(m)
    }
    state.set(n, 2)
  }
  const hasIn = new Set(edges.filter((e) => out.has(e.from) && out.has(e.to)).map((e) => e.to))
  for (const n of nodeIds) if (!hasIn.has(n) && !state.has(n)) visit(n)
  for (const n of nodeIds) if (!state.has(n)) visit(n)
  const next = new Map(nodeIds.map((n) => [n, []]))
  for (const [a, b] of forward) {
    next.get(a).push(b)
    indeg.set(b, indeg.get(b) + 1)
  }
  const depth = new Map(nodeIds.map((n) => [n, 0]))
  const queue = nodeIds.filter((n) => indeg.get(n) === 0)
  while (queue.length) {
    const n = queue.shift()
    for (const m of next.get(n)) {
      depth.set(m, Math.max(depth.get(m), depth.get(n) + 1))
      indeg.set(m, indeg.get(m) - 1)
      if (indeg.get(m) === 0) queue.push(m)
    }
  }
  return depth
}

/** Positions (left to right by layer, top to bottom inside a layer) for one group of nodes. */
export function layout(nodes, edges, { vertical = false } = {}) {
  const ids = nodes.map((n) => n.id)
  const depth = layers(ids, edges)
  const byLayer = new Map()
  for (const n of nodes) {
    const d = depth.get(n.id)
    if (!byLayer.has(d)) byLayer.set(d, [])
    byLayer.get(d).push(n.id)
  }
  const tallest = Math.max(...[...byLayer.values()].map((l) => l.length))
  const pos = {}
  for (const [d, list] of byLayer) {
    const offset = ((tallest - list.length) * (NODE_H + GAP_Y)) / 2
    list.forEach((id, i) => {
      const along = d * (NODE_W + GAP_X)
      const across = offset + i * (NODE_H + GAP_Y)
      pos[id] = vertical ? { x: across, y: along } : { x: along, y: across }
    })
  }
  const width = (Math.max(...byLayer.keys()) + 1) * (NODE_W + GAP_X) - GAP_X
  const height = tallest * (NODE_H + GAP_Y) - GAP_Y
  return { pos, width: vertical ? height : width, height: vertical ? width : height }
}

/** Cubic path from the right side of one node to the left side of the next (or a loop path when the target is to the left). */
export function edgePath(a, b) {
  const x1 = a.x + NODE_W
  const y1 = a.y + NODE_H / 2
  const x2 = b.x
  const y2 = b.y + NODE_H / 2
  if (x2 <= a.x) {
    const top = Math.min(a.y, b.y) - 22
    return `M ${a.x + NODE_W / 2} ${a.y} C ${a.x + NODE_W / 2} ${top}, ${b.x + NODE_W / 2} ${top}, ${b.x + NODE_W / 2} ${b.y}`
  }
  const mid = (x1 + x2) / 2
  return `M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`
}

const BY_TYPE = { node_start: 'active', node_end: 'done', node_error: 'failed', node_wait: 'waiting' }

/** {path: {state, seconds, at}} from a list of events (later events win). */
export function nodeStates(events) {
  const out = {}
  for (const e of events) {
    const s = BY_TYPE[e.type]
    if (!s || !e.node_path) continue
    out[e.node_path] = { state: s, seconds: e.payload?.seconds ?? out[e.node_path]?.seconds, at: e.ts, message: s === 'failed' ? e.message : undefined }
  }
  return out
}

/** Student ids seen in the events, in order of first appearance, with a summary of how far each is. */
export function studentsIn(events) {
  const seen = new Map()
  for (const e of events) {
    const m = /^student:([^/]+)/.exec(e.node_path || '')
    if (!m) continue
    if (!seen.has(m[1])) seen.set(m[1], { id: m[1], state: 'active', failed: false })
    const s = seen.get(m[1])
    if (e.type === 'node_error') s.failed = true
    if (e.type === 'node_end' && e.node_path === `student:${m[1]}/export`) s.state = 'done'
  }
  return [...seen.values()].map((s) => (s.failed && s.state !== 'done' ? { ...s, state: 'failed' } : s))
}

/** State of an edge: flowing while its target is active and its source is done. */
export function edgeState(from, to) {
  const a = from?.state
  const b = to?.state
  if (a === 'done' && (b === 'active' || b === 'waiting')) return 'flowing'
  if (a === 'done' && b === 'done') return 'done'
  if (b === 'failed') return 'failed'
  return 'idle'
}

/** The path of a topology node for a given student lane (or the team). */
export function pathOf(node, student) {
  if (node.group === 'team') return `team/${node.id}`
  if (node.group === 'student') return `student:${student}/${node.id}`
  return `student:${student}/rf_subagent/${node.id}`
}

// ---- the vertical view -------------------------------------------------------------------------------------------------------------

/** The team run as an ordered list of steps (the order of the topology). */
export function teamSteps(topology) {
  return topology.nodes.filter((n) => n.group === 'team')
}

/** The student lane as rows: nodes that run side by side (the factors) share a row, rows run top to bottom. */
export function laneRows(topology) {
  const nodes = topology.nodes.filter((n) => n.group === 'student')
  const edges = topology.edges.filter((e) => e.group === 'student')
  const depth = layers(nodes.map((n) => n.id), edges)
  const rows = []
  for (const n of nodes) {
    const d = depth.get(n.id)
    ;(rows[d] ||= []).push(n)
  }
  return rows.filter(Boolean)
}

/** State of a row of nodes as one: failed if any failed, waiting, active if any is running, done when all are, else idle. */
export function rowState(row, states, student) {
  const s = row.map((n) => states[pathOf(n, student)]?.state || 'idle')
  if (s.includes('failed')) return 'failed'
  if (s.includes('waiting')) return 'waiting'
  if (s.includes('active')) return 'active'
  if (s.every((x) => x === 'done')) return 'done'
  return s.some((x) => x === 'done') ? 'active' : 'idle'
}

/** The last log line a node wrote, for the one-line caption under its name. */
export function lastLine(events, path) {
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i]
    if (e.node_path === path && e.type === 'log') return e.message
  }
  return ''
}

/** What the Requirement Fulfillment sub-agent did for one student: the tasks it judged, the model calls it made, and what the provider refused. */
export function rfSummary(events, student) {
  const path = `student:${student}/rf_subagent`
  const tasks = new Map()
  let calls = 0
  let errors = 0
  let tokens = 0
  for (const e of events) {
    if (e.node_path !== path) continue
    const m = e.message || ''
    let t
    if ((t = /^task_start: judging task (\S+)/.exec(m))) tasks.set(t[1], { id: t[1], state: 'judging' })
    else if ((t = /^task_done: task (\S+): fulfilment ([\d.]+)/.exec(m))) tasks.set(t[1], { id: t[1], state: 'done', fulfilment: Number(t[2]) })
    else if ((t = /^task_skipped: task (\S+)/.exec(m))) tasks.set(t[1], { id: t[1], state: 'skipped' })
    else if ((t = /^task_error: task (\S+)/.exec(m))) tasks.set(t[1], { id: t[1], state: 'error' })
    else if (/^llm_call:/.test(m)) {
      calls++
      const k = /: (\d+)\+(\d+) tokens/.exec(m)
      if (k) tokens += Number(k[1]) + Number(k[2])
    } else if (/^llm_error:/.test(m)) errors++
  }
  return { tasks: [...tasks.values()], calls, errors, tokens }
}

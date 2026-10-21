// A small top-to-bottom layout for the workflow and agent graphs (a handful of nodes each), so the diagram is plain SVG and needs no library.
//
// Nodes are placed in rows by their longest path from the start. A loop (an edge back to an earlier row) and an edge that skips rows are drawn
// as curves round the side, so nothing runs through a node. `rowExtra[r]` adds free space below row r (room for a nested graph).

export const DEFAULTS = { nodeW: 168, nodeH: 44, gapX: 28, gapY: 36, pad: 20, side: 70 }

const key = (from, to) => `${from}>${to}`

// Edges that point back to a node still being visited are loops; they do not take part in the row calculation.
export function findLoops(nodes, edges) {
  const out = new Map(nodes.map((n) => [n, []]))
  for (const e of edges) out.get(e.from)?.push(e.to)
  const state = new Map()
  const loops = new Set()
  const visit = (n) => {
    state.set(n, 1)
    for (const m of out.get(n) ?? []) {
      if (state.get(m) === 1) loops.add(key(n, m))
      else if (!state.has(m)) visit(m)
    }
    state.set(n, 2)
  }
  const start = nodes.includes('__start__') ? '__start__' : nodes[0]
  if (start !== undefined) visit(start)
  for (const n of nodes) if (!state.has(n)) visit(n)
  return loops
}

export function rowsOf(nodes, edges, loops = findLoops(nodes, edges)) {
  const level = new Map(nodes.map((n) => [n, 0]))
  const forward = edges.filter((e) => !loops.has(key(e.from, e.to)) && level.has(e.from) && level.has(e.to))
  for (let i = 0; i < nodes.length; i += 1) {
    let changed = false
    for (const e of forward) {
      if (level.get(e.to) < level.get(e.from) + 1) {
        level.set(e.to, level.get(e.from) + 1)
        changed = true
      }
    }
    if (!changed) break
  }
  return level
}

export function layoutGraph(nodes, edges, options = {}) {
  const { nodeW, nodeH, gapX, gapY, pad, side } = { ...DEFAULTS, ...options }
  const rowExtra = options.rowExtra ?? []
  const loops = findLoops(nodes, edges)
  const level = rowsOf(nodes, edges, loops)
  const rows = []
  for (const n of nodes) (rows[level.get(n)] ??= []).push(n)
  const widest = Math.max(1, ...rows.map((r) => r?.length ?? 0))
  const innerW = widest * nodeW + (widest - 1) * gapX
  const width = innerW + 2 * pad + 2 * side
  const centerX = width / 2

  const rowTop = []
  let y = pad
  rows.forEach((_, r) => {
    rowTop[r] = y
    y += nodeH + gapY + (rowExtra[r] ?? 0)
  })
  const height = y - gapY + pad

  const placed = new Map()
  rows.forEach((row, r) => {
    const rowW = row.length * nodeW + (row.length - 1) * gapX
    row.forEach((id, i) => placed.set(id, { id, level: r, x: centerX - rowW / 2 + i * (nodeW + gapX), y: rowTop[r], w: nodeW, h: nodeH }))
  })

  const left = Math.min(...[...placed.values()].map((p) => p.x)) - side / 2
  const right = Math.max(...[...placed.values()].map((p) => p.x + p.w)) + side / 2
  const rowMin = rows.map((row) => Math.min(...row.map((id) => placed.get(id).x)))
  const rowMax = rows.map((row) => Math.max(...row.map((id) => placed.get(id).x)))
  // A loop or a skipping edge leaves and enters by the left or right side of a node that is the outermost of its row on that side, so the curve
  // runs through the margin and never through a neighbour. If no side fits both ends, it is drawn like an ordinary edge.
  const sideFor = (a, b) => {
    if (a.x === rowMin[a.level] && b.x === rowMin[b.level]) return 'left'
    if (a.x === rowMax[a.level] && b.x === rowMax[b.level]) return 'right'
    return null
  }
  const laid = edges
    .filter((e) => placed.has(e.from) && placed.has(e.to))
    .map((e) => {
      const a = placed.get(e.from)
      const b = placed.get(e.to)
      const loop = loops.has(key(e.from, e.to))
      const skip = !loop && b.level - a.level > 1
      const around = loop || skip ? sideFor(a, b) : null
      let d
      if (around) {
        const bulge = around === 'left' ? left : right
        const xa = around === 'left' ? a.x : a.x + a.w
        const xb = around === 'left' ? b.x : b.x + b.w
        d = `M ${xa} ${a.y + a.h / 2} C ${bulge} ${a.y + a.h / 2}, ${bulge} ${b.y + b.h / 2}, ${xb} ${b.y + b.h / 2}`
      } else {
        const x1 = a.x + a.w / 2
        const x2 = b.x + b.w / 2
        const up = b.level <= a.level
        const y1 = up ? a.y : a.y + a.h
        const y2 = up ? b.y + b.h : b.y
        const pull = up ? -gapY : gapY / 2
        d = `M ${x1} ${y1} C ${x1} ${y1 + pull}, ${x2} ${y2 - pull}, ${x2} ${y2}`
      }
      return { from: e.from, to: e.to, conditional: Boolean(e.conditional), kind: loop ? 'loop' : skip ? 'skip' : 'forward', side: around, d }
    })
  return { width, height, nodes: [...placed.values()], edges: laid, rows: rows.length }
}

import { describe, expect, it } from 'vitest'
import {
  AGENTS,
  auditFacts,
  canSeeAudit,
  describeRejected,
  indicatorRows,
  nodeLabel,
  nodeStyle,
  optionsLabel,
  pageOf,
  rejectedCount,
  scrutinyMeaning,
  scrutinyTone,
  trailAgents,
} from './agents.js'
import { findLoops, layoutGraph, rowsOf } from './graphLayout.js'

describe('trails', () => {
  it('lists the three agents in the order of the flow, with their entries', () => {
    const rows = trailAgents({ Governance: [{ step: 1 }], 'Analysis Orchestrator': [{ step: 1 }, { step: 2 }] })
    expect(rows.map((r) => r.title)).toEqual(['Analysis Orchestrator', 'Question Agent', 'Governance'])
    expect(rows.map((r) => r.entries.length)).toEqual([2, 0, 1])
    expect(AGENTS.every((a) => a.goal)).toBe(true)
    expect(trailAgents(undefined).every((r) => r.entries.length === 0)).toBe(true)
  })

  it('counts and describes rejected choices', () => {
    expect(rejectedCount([{ rejected: null }, { rejected: { policy: 'p' } }, {}])).toBe(1)
    expect(rejectedCount(undefined)).toBe(0)
    expect(describeRejected({ policy: 'rogue', proposed: 'shell:rm -rf /', problem: 'not one of the valid options' })).toBe(
      'The policy "rogue" proposed "shell:rm -rf /": not one of the valid options. The rules decided instead.',
    )
    expect(describeRejected(null)).toBe('')
    expect(optionsLabel(['a', 'b'])).toBe('a | b')
    expect(optionsLabel([])).toBe('none')
  })
})

describe('governance wording', () => {
  it('says what each scrutiny level means with the thresholds of the run', () => {
    expect(scrutinyMeaning({ level: 'normal', score: 0, elevated_at: 3, high_at: 6 })).toBe('Score 0: below 3, so calls get the normal check.')
    expect(scrutinyMeaning({ level: 'elevated', score: 5, elevated_at: 3, high_at: 6 })).toMatch(/reached 3.*second, stricter check/)
    expect(scrutinyMeaning({ level: 'high', score: 7, elevated_at: 3, high_at: 6 })).toMatch(/flagged for human review/)
    expect(scrutinyMeaning(undefined)).toBe('Not recorded.')
    expect([scrutinyTone('normal'), scrutinyTone('elevated'), scrutinyTone('high'), scrutinyTone('x')]).toEqual(['success', 'warning', 'danger', 'neutral'])
  })

  it('keeps only the facts of an indicator', () => {
    expect(indicatorRows([{ kind: 'readme', source: 'README.md', pattern: 'p', count: 2, text: 'the text of the README' }])).toEqual([
      { kind: 'readme', source: 'README.md', pattern: 'p', count: 2 },
    ])
    expect(indicatorRows(undefined)).toEqual([])
  })
})

describe('audit lines', () => {
  it('cuts hashes to twelve characters and shows nested values only by size', () => {
    const facts = auditFacts({
      seq: 3, event: 'pre_send_check', call: 'interpret', prompt_sha256: 'a'.repeat(64), evidence_ids_offered: ['E1', 'E2'], state: { a: 1, b: 2 }, note: null, ok: true, n: 0,
    })
    const by = Object.fromEntries(facts.map((f) => [f.name, f]))
    expect(by.prompt_sha256).toEqual({ name: 'prompt_sha256', value: `${'a'.repeat(12)}…`, hash: true })
    expect(by.evidence_ids_offered.value).toBe('2 items')
    expect(by.state.value).toBe('2 fields')
    expect(by.ok.value).toBe('true')
    expect(by.n.value).toBe('0')
    expect(by.call.value).toBe('interpret')
    expect(by.note).toBeUndefined()
    expect(by.seq).toBeUndefined()
    expect(by.event).toBeUndefined()
    expect(auditFacts({ seq: 1, event: 'x', list: ['a'] })[0].value).toBe('1 item')
  })

  it('never carries a full hash into the page', () => {
    const full = 'f'.repeat(64)
    expect(JSON.stringify(auditFacts({ seq: 1, event: 'e', prompt_sha256: full, other_hash: full }))).not.toContain(full)
  })

  it('pages the lines and clamps the page', () => {
    const lines = Array.from({ length: 60 }, (_, i) => ({ seq: i }))
    expect(pageOf(lines, 0).rows).toHaveLength(25)
    expect(pageOf(lines, 2)).toMatchObject({ page: 2, pages: 3, total: 60 })
    expect(pageOf(lines, 2).rows).toHaveLength(10)
    expect(pageOf(lines, 99).page).toBe(2)
    expect(pageOf(lines, -3).page).toBe(0)
    expect(pageOf(undefined, 0)).toEqual({ rows: [], page: 0, pages: 1, total: 0 })
  })

  it('lets only lecturers and administrators see it', () => {
    expect(['student', 'instructor', 'admin', null, undefined].map(canSeeAudit)).toEqual([false, true, true, false, false])
  })
})

describe('node colours', () => {
  it('draws a skipped or not-run node dashed so it never looks completed', () => {
    expect(nodeStyle('completed')[0]).not.toContain('dasharray')
    expect(nodeStyle('skipped')[0]).toContain('dasharray')
    expect(nodeStyle('not run')[0]).toContain('dasharray')
    expect(nodeStyle('failed')[0]).toContain('red')
    expect(nodeStyle('completed')[0]).toContain('emerald')
    expect(nodeStyle('partial')[0]).toContain('amber')
    expect(nodeStyle(undefined)[1]).toBe('')
    expect(new Set(['completed', 'failed', 'skipped', 'not run'].map((s) => nodeStyle(s)[0])).size).toBe(4)
  })

  it('labels nodes', () => {
    expect(nodeLabel('__start__')).toBe('start')
    expect(nodeLabel('__end__')).toBe('end')
    expect(nodeLabel('follow_up')).toBe('follow up')
    expect(nodeLabel('scan', { scan: 'Scan' })).toBe('Scan')
  })
})

describe('graph layout', () => {
  const chain = ['__start__', 'a', 'b', 'c', '__end__']
  const chainEdges = [['__start__', 'a'], ['a', 'b'], ['b', 'c'], ['c', '__end__']].map(([from, to]) => ({ from, to }))

  it('puts a chain in rows, top to bottom, in one column', () => {
    const g = layoutGraph(chain, chainEdges)
    expect(g.nodes.map((n) => n.level)).toEqual([0, 1, 2, 3, 4])
    expect(new Set(g.nodes.map((n) => n.x)).size).toBe(1)
    expect(g.nodes.map((n) => n.y)).toEqual([...g.nodes.map((n) => n.y)].sort((a, b) => a - b))
    expect(g.edges.every((e) => e.kind === 'forward')).toBe(true)
  })

  it('finds a loop and keeps it out of the row calculation', () => {
    const nodes = ['__start__', 'plan', 'act', 'update', 'stop']
    const edges = [['__start__', 'plan'], ['plan', 'act'], ['act', 'update'], ['update', 'plan'], ['update', 'stop']].map(([from, to]) => ({ from, to }))
    expect([...findLoops(nodes, edges)]).toEqual(['update>plan'])
    const g = layoutGraph(nodes, edges)
    expect(g.nodes.find((n) => n.id === 'stop').level).toBe(4)
    expect(g.edges.find((e) => e.from === 'update' && e.to === 'plan').kind).toBe('loop')
  })

  it('draws an edge that skips rows round the side and branches side by side', () => {
    const nodes = ['s', 'a', 'b', 'c', 'd']
    const edges = [['s', 'a'], ['a', 'b'], ['a', 'c'], ['b', 'd'], ['c', 'd'], ['s', 'd']].map(([from, to]) => ({ from, to }))
    const g = layoutGraph(nodes, edges)
    expect(g.edges.find((e) => e.from === 's' && e.to === 'd').kind).toBe('skip')
    const [b, c] = ['b', 'c'].map((id) => g.nodes.find((n) => n.id === id))
    expect(b.y).toBe(c.y)
    expect(b.x).not.toBe(c.x)
    expect(rowsOf(nodes, edges).get('d')).toBe(3)
  })

  it('keeps every node inside the drawing and never lets two nodes overlap', () => {
    const nodes = ['s', 'a', 'b', 'c', 'd', 'e']
    const edges = [['s', 'a'], ['a', 'b'], ['a', 'c'], ['a', 'd'], ['b', 'e'], ['c', 'e'], ['d', 'e']].map(([from, to]) => ({ from, to }))
    const g = layoutGraph(nodes, edges)
    for (const n of g.nodes) {
      expect(n.x).toBeGreaterThanOrEqual(0)
      expect(n.x + n.w).toBeLessThanOrEqual(g.width)
      expect(n.y + n.h).toBeLessThanOrEqual(g.height)
    }
    for (const a of g.nodes) for (const b of g.nodes) if (a !== b) expect(a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h).toBe(false)
  })

  it('makes room under a row for a nested graph', () => {
    const plain = layoutGraph(chain, chainEdges)
    const roomy = layoutGraph(chain, chainEdges, { rowExtra: [0, 100] })
    expect(roomy.nodes.find((n) => n.id === 'b').y - plain.nodes.find((n) => n.id === 'b').y).toBe(100)
    expect(roomy.nodes.find((n) => n.id === 'a').y).toBe(plain.nodes.find((n) => n.id === 'a').y)
    expect(roomy.height - plain.height).toBe(100)
  })

  it('copes with an empty graph and with edges to unknown nodes', () => {
    expect(layoutGraph([], []).nodes).toEqual([])
    expect(layoutGraph(['a'], [{ from: 'a', to: 'zzz' }]).edges).toEqual([])
  })
})

describe('graph layout: routing round the side', () => {
  it('sends a loop and a skipping edge through the margin of the outermost node, never through a neighbour', () => {
    // plan -> act -> update -> plan (loop); update shares its row with end, update is the leftmost
    const nodes = ['__start__', 'plan', 'act', 'stop', 'update', 'end']
    const edges = [['__start__', 'plan'], ['plan', 'act'], ['plan', 'stop'], ['act', 'update'], ['update', 'plan'], ['stop', 'end'], ['update', 'end']].map(([from, to]) => ({ from, to }))
    const g = layoutGraph(nodes, edges)
    const loop = g.edges.find((e) => e.kind === 'loop')
    expect(loop.side).toBe('left')
    const update = g.nodes.find((n) => n.id === 'update')
    expect(loop.d.startsWith(`M ${update.x} `)).toBe(true) // leaves by the left edge of the leftmost node
    const leftMost = Math.min(...g.nodes.map((n) => n.x))
    expect(Number(/C ([\d.]+) /.exec(loop.d)[1])).toBeLessThan(leftMost)
  })

  it('draws an edge from the middle of a row like an ordinary edge, since no side is free', () => {
    const nodes = ['s', 'a', 'b', 'c', 'm', 'e']
    const edges = [['s', 'a'], ['s', 'b'], ['s', 'c'], ['a', 'm'], ['b', 'm'], ['c', 'm'], ['m', 'e'], ['b', 'e']].map(([from, to]) => ({ from, to }))
    const g = layoutGraph(nodes, edges)
    const skip = g.edges.find((x) => x.from === 'b' && x.to === 'e')
    expect(skip.kind).toBe('skip')
    expect(skip.side).toBe(null)
    expect(skip.d.startsWith('M ')).toBe(true)
  })
})

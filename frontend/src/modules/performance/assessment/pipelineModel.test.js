import { describe, expect, it } from 'vitest'
import { edgePath, edgeState, laneRows, lastLine, layers, layout, llmSummary, NODE_H, NODE_W, nodeStates, pathOf, producedFields, rfSummary, rowState, studentsIn, teamSteps } from './pipelineModel.js'

const nodes = ['check', 'a', 'b', 'join', 'next'].map((id) => ({ id }))
const edges = [
  { from: 'check', to: 'a' }, { from: 'check', to: 'b' }, { from: 'a', to: 'join' }, { from: 'b', to: 'join' }, { from: 'join', to: 'next' },
]

describe('layers and layout', () => {
  it('puts parallel nodes in the same layer and joins after them', () => {
    const d = layers(nodes.map((n) => n.id), edges)
    expect([d.get('check'), d.get('a'), d.get('b'), d.get('join'), d.get('next')]).toEqual([0, 1, 1, 2, 3])
  })

  it('ignores a loop back to an earlier node', () => {
    const d = layers(['x', 'y', 'z'], [{ from: 'x', to: 'y' }, { from: 'y', to: 'z' }, { from: 'z', to: 'y' }])
    expect([d.get('x'), d.get('y'), d.get('z')]).toEqual([0, 1, 2])
  })

  it('gives every node its own place and centres a short layer', () => {
    const { pos, width, height } = layout(nodes, edges)
    const places = new Set(Object.values(pos).map((p) => `${p.x},${p.y}`))
    expect(places.size).toBe(nodes.length)
    expect(pos.check.y).toBeGreaterThan(0) // one node next to two is centred
    expect(pos.a.x).toBe(pos.b.x)
    expect(width).toBeGreaterThan(3 * NODE_W)
    expect(height).toBeGreaterThanOrEqual(2 * NODE_H)
  })

  it('draws a forward edge from the right of a node to the left of the next, and a loop above', () => {
    const forward = edgePath({ x: 0, y: 0 }, { x: 300, y: 60 })
    expect(forward.startsWith(`M ${NODE_W} ${NODE_H / 2}`)).toBe(true)
    expect(forward.endsWith('300 83')).toBe(true)
    expect(edgePath({ x: 300, y: 0 }, { x: 0, y: 0 })).toContain('-22')
  })
})

describe('events to states', () => {
  const ev = (type, node_path, extra = {}) => ({ type, node_path, ts: 't', payload: {}, message: '', ...extra })

  it('follows start, end, error and wait of each path', () => {
    const s = nodeStates([
      ev('node_start', 'team/a'), ev('node_end', 'team/a', { payload: { seconds: 1.5 } }),
      ev('node_start', 'team/b'), ev('node_error', 'team/b', { message: 'boom' }),
      ev('node_start', 'team/c'), ev('node_wait', 'team/c'),
      ev('log', 'team/d'),
    ])
    expect(s['team/a']).toMatchObject({ state: 'done', seconds: 1.5 })
    expect(s['team/b']).toMatchObject({ state: 'failed', message: 'boom' })
    expect(s['team/c'].state).toBe('waiting')
    expect(s['team/d']).toBeUndefined()
  })

  it('lists the students in order and marks finished and failed ones', () => {
    const list = studentsIn([
      ev('node_start', 'student:S2/check'), ev('node_start', 'student:S1/check'), ev('node_end', 'student:S1/export'),
      ev('node_error', 'student:S2'), ev('node_start', 'team/x'),
    ])
    expect(list).toEqual([{ id: 'S2', state: 'failed', failed: true }, { id: 'S1', state: 'done', failed: false }])
  })

  it('lights an edge only while its source is done and its target is running', () => {
    expect(edgeState({ state: 'done' }, { state: 'active' })).toBe('flowing')
    expect(edgeState({ state: 'done' }, { state: 'waiting' })).toBe('flowing')
    expect(edgeState({ state: 'done' }, { state: 'done' })).toBe('done')
    expect(edgeState({ state: 'active' }, undefined)).toBe('idle')
    expect(edgeState(undefined, { state: 'failed' })).toBe('failed')
  })

  it('builds the event path of a node for the team, a student lane and the sub-agent', () => {
    expect(pathOf({ id: 'publish', group: 'team' })).toBe('team/publish')
    expect(pathOf({ id: 'fusion', group: 'student' }, 'S1')).toBe('student:S1/fusion')
    expect(pathOf({ id: 'decide', group: 'rf' }, 'S1')).toBe('student:S1/rf_subagent/decide')
  })
})

describe('the vertical view', () => {
  const topology = {
    nodes: [
      { id: 'a', group: 'team' }, { id: 'b', group: 'team' },
      { id: 'check', group: 'student' }, { id: 'f1', group: 'student' }, { id: 'f2', group: 'student' }, { id: 'join', group: 'student' }, { id: 'export', group: 'student' },
    ],
    edges: [
      { from: 'check', to: 'f1', group: 'student' }, { from: 'check', to: 'f2', group: 'student' }, { from: 'f1', to: 'join', group: 'student' }, { from: 'f2', to: 'join', group: 'student' },
      { from: 'join', to: 'export', group: 'student' },
    ],
  }

  it('puts the steps of the team run in order and the factors side by side in one row', () => {
    expect(teamSteps(topology).map((n) => n.id)).toEqual(['a', 'b'])
    expect(laneRows(topology).map((r) => r.map((n) => n.id))).toEqual([['check'], ['f1', 'f2'], ['join'], ['export']])
  })

  it('shows a row as one state', () => {
    const row = [{ id: 'f1', group: 'student' }, { id: 'f2', group: 'student' }]
    const at = (a, b) => ({ 'student:S/f1': a && { state: a }, 'student:S/f2': b && { state: b } })
    expect(rowState(row, at(undefined, undefined), 'S')).toBe('idle')
    expect(rowState(row, at('done', 'done'), 'S')).toBe('done')
    expect(rowState(row, at('done', 'active'), 'S')).toBe('active')
    expect(rowState(row, at('done', undefined), 'S')).toBe('active') // one finished, the other not started yet: still in progress
    expect(rowState(row, at('done', 'failed'), 'S')).toBe('failed')
    expect(rowState(row, at('waiting', 'active'), 'S')).toBe('waiting')
  })

  it('reads the last log line of a node', () => {
    const ev = [{ node_path: 'team/a', type: 'log', message: 'one' }, { node_path: 'team/a', type: 'tool', message: 'tool' }, { node_path: 'team/a', type: 'log', message: 'two' }, { node_path: 'team/b', type: 'log', message: 'other' }]
    expect(lastLine(ev, 'team/a')).toBe('two')
    expect(lastLine(ev, 'team/zzz')).toBe('')
  })

  it('summarises the Requirement Fulfillment sub-agent from its log lines', () => {
    const p = 'student:S/rf_subagent'
    const ev = [
      { node_path: p, message: 'task_start: judging task T1' }, { node_path: p, message: 'llm_call: agent:map:T1: 1000+50 tokens, 1.2s' }, { node_path: p, message: 'llm_call: agent:decide:T1:C1:0: 2000+60 tokens, 2.0s' },
      { node_path: p, message: 'llm_error: agent:decide:T1:C2:final: bad_request: HTTP 400' }, { node_path: p, message: 'task_done: task T1: fulfilment 0.25' }, { node_path: p, message: 'task_start: judging task T2' },
      { node_path: 'student:OTHER/rf_subagent', message: 'task_start: judging task X' },
    ]
    expect(rfSummary(ev, 'S')).toEqual({ tasks: [{ id: 'T1', state: 'done', fulfilment: 0.25 }, { id: 'T2', state: 'judging' }], calls: 2, errors: 1, tokens: 3110 })
  })

  it('uses typed task, model and produced payloads without parsing messages', () => {
    const ev = (type, node_path, extra = {}) => ({ type, node_path, ts: 't', payload: {}, message: '', ...extra })
    const events = [
      ev('task', 'student:S/rf_subagent', { payload: { event: 'task_done', task: 'T1', fulfilment: 0.75 } }),
      ev('llm', 'student:S/rf_subagent', { payload: { prompt_tokens: 10, completion_tokens: 4 } }),
      ev('produce', 'student:S/narrate', { payload: { field: 'brief.text', verified: true, fallback: false } }),
      ev('produce', 'student:S/narrate', { payload: { field: 'why.key', verified: false, fallback: true } }),
    ]
    expect(rfSummary(events, 'S').tasks).toEqual([{ id: 'T1', state: 'done', fulfilment: 0.75 }])
    expect(llmSummary(events, 'student:S/rf_subagent')).toEqual({ calls: 1, tokens: 14 })
    expect(producedFields(events, 'student:S/narrate')).toEqual({
      'brief.text': { verified: true, fallback: false },
      'why.key': { verified: false, fallback: true },
    })
  })
})

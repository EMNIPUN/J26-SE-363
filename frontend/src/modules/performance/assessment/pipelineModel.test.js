import { describe, expect, it } from 'vitest'
import { edgePath, edgeState, layers, layout, NODE_H, NODE_W, nodeStates, pathOf, studentsIn } from './pipelineModel.js'

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

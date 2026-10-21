import { describe, expect, it } from 'vitest'
import { runStats } from './runStats.js'

const run = (id, status, mode, start, end, extra = {}) => ({ id, status, mode, started_at: start && `2026-04-13T${start}:00Z`, finished_at: end && `2026-04-13T${end}:00Z`, created_at: '2026-04-13T08:00:00Z', ...extra })
const runs = [
  run('d', 'running', 'snapshot', '12:00', null),
  run('c', 'failed', 'snapshot', '11:00', '11:03'),
  run('b', 'succeeded', 'final', '10:00', '10:20', { summary: { students: 4 } }),
  run('a', 'succeeded', 'snapshot', '09:00', '09:10', { summary: { students: 4 } }),
]

describe('what the runs add up to', () => {
  const s = runStats(runs)
  it('counts them by kind and outcome', () => {
    expect(s).toMatchObject({ total: 4, snapshots: 3, finals: 1, succeeded: 2, failed: 1, active: 1, students: 4 })
    expect(s.latest.id).toBe('d')
  })
  it('works out the success rate over the runs that ended, not the one still going', () => {
    expect(s.successRate).toBeCloseTo(2 / 3)
  })
  it('times the finished runs', () => {
    expect(s).toMatchObject({ averageSeconds: 900, fastestSeconds: 600, slowestSeconds: 1200 })
  })
  it('lists durations oldest first for a chart', () => {
    expect(s.durations.map((d) => d.id)).toEqual(['a', 'b', 'c']) // the running one has no end yet
  })
  it('copes with no runs', () => {
    expect(runStats([])).toMatchObject({ total: 0, successRate: null, averageSeconds: null, latest: null, durations: [] })
    expect(runStats(undefined).total).toBe(0)
  })
})

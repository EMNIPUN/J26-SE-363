import { describe, expect, it } from 'vitest'
import { developmentModel, sprintProgress } from './development.js'

const pt = (day, mark, extra = {}) => ({ as_of: `2026-04-${day}T20:00:00Z`, mark, mark_interval: [mark - 10, mark + 10], factors: { effort: { score: mark / 100 } }, ...extra })
const rows = [{ student_id: 'a', student: { name: 'Ann' } }, { student_id: 'b', student: { name: 'Bob' } }, { student_id: 'c', student: { name: 'Cy' } }]
const series = [
  [pt('11', 40), pt('12', 55), pt('13', 70)],
  [pt('11', 60), pt('12', 80), pt('13', 66)],
  [pt('11', 20), pt('13', 30, { mark_interval: [5, 55] })],
]

describe('how a team developed', () => {
  const m = developmentModel(rows, series)

  it('follows each student and calls a change of five points a rise or a fall', () => {
    const by = Object.fromEntries(m.students.map((s) => [s.name, s]))
    expect(by.Ann).toMatchObject({ first: 40, latest: 70, change: 30, trend: 'rising' })
    expect(by.Bob).toMatchObject({ first: 60, latest: 66, change: 6, lastChange: -14, trend: 'rising' })
    expect(by.Cy).toMatchObject({ change: 10, trend: 'rising' })
  })

  it('averages the team per day and keeps the lowest and highest as a band', () => {
    expect(m.chart.map((r) => r.day)).toEqual(['2026-04-11', '2026-04-12', '2026-04-13'])
    expect(m.chart[0]).toMatchObject({ average: 40, low: 20, high: 60, band: [20, 60], Ann: 40, Bob: 60, Cy: 20 })
    expect(m.chart[1].Cy).toBeNull() // no snapshot that day: the line is drawn across it
    expect(m.team).toMatchObject({ snapshots: 3, first: 40, latest: 55, change: 15 })
  })

  it('averages a factor over the team for each day', () => {
    expect(m.factorsByDay[0].effort).toBe(40)
    expect(m.factorsByDay[0].consistency).toBeNull()
  })

  it('names the students worth a look, and why', () => {
    const kinds = m.warnings.map((w) => `${w.name}:${w.kind}`)
    expect(kinds).toContain('Bob:dropped')
    expect(kinds).toContain('Cy:low')
    expect(kinds).toContain('Cy:uncertain')
    expect(kinds).not.toContain('Ann:low')
    expect(m.team.improved.name).toBe('Ann')
    expect(m.team.lowCount).toBe(1)
  })

  it('copes with a team that has no snapshots yet', () => {
    const none = developmentModel(rows, [[], [], []])
    expect(none.days).toEqual([])
    expect(none.team).toMatchObject({ snapshots: 0, latest: null, change: null })
    expect(developmentModel(undefined, undefined).students).toEqual([])
  })
})

describe('how far through the sprint', () => {
  const sprint = { start: '2026-04-10', end: '2026-04-19' }
  it('is a share between 0 and 1, with the day number', () => {
    const mid = sprintProgress(sprint, new Date('2026-04-14T12:00:00').getTime())
    expect(mid.share).toBeGreaterThan(0.4)
    expect(mid.share).toBeLessThan(0.6)
    expect(mid).toMatchObject({ days: 10, over: false, notStarted: false })
    expect(sprintProgress(sprint, new Date('2026-05-01').getTime())).toMatchObject({ share: 1, over: true })
    expect(sprintProgress(sprint, new Date('2026-04-01').getTime())).toMatchObject({ share: 0, notStarted: true })
    expect(sprintProgress(null)).toBeNull()
  })
})

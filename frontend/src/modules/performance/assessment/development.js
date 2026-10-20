import { FACTORS } from './format.js'

export const STUDENT_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#0ea5e9', '#8b5cf6', '#14b8a6', '#f43f5e']

const dayKey = (iso) => new Date(iso).toISOString().slice(0, 10)
const round = (n) => Math.round(n)
const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null)

/**
 * How a team developed over a sprint, worked out from the snapshots of every student (`series[i]` belongs to `rows[i]`).
 * Several snapshots on one day count as the last of that day. A change of 5 points or more is a rise or a fall; the rest is steady.
 */
export function developmentModel(rows, series) {
  const students = (rows || []).map((r, i) => {
    const byDay = new Map()
    ;[...(series?.[i] || [])].sort((a, b) => new Date(a.as_of) - new Date(b.as_of)).forEach((p) => {
      if (p.mark == null) return
      byDay.set(dayKey(p.as_of), { day: dayKey(p.as_of), t: new Date(p.as_of).getTime(), mark: p.mark, interval: p.mark_interval, factors: p.factors || {} })
    })
    const points = [...byDay.values()]
    const first = points[0]?.mark ?? null
    const latest = points.at(-1)?.mark ?? null
    const previous = points.length > 1 ? points.at(-2).mark : null
    const change = first != null && latest != null && points.length > 1 ? latest - first : null
    const lastChange = previous != null ? latest - previous : null
    const width = points.at(-1)?.interval ? points.at(-1).interval[1] - points.at(-1).interval[0] : null
    return {
      id: r.student_id, name: r.student?.name || r.student_id, picture: r.student?.picture ?? null, color: STUDENT_COLORS[i % STUDENT_COLORS.length], points,
      first, latest, previous, change, lastChange, width,
      trend: change == null ? 'none' : change >= 5 ? 'rising' : change <= -5 ? 'falling' : 'steady',
    }
  })

  const days = [...new Set(students.flatMap((s) => s.points.map((p) => p.day)))].sort()
  const chart = days.map((day) => {
    const marks = students.map((s) => s.points.find((p) => p.day === day)?.mark).filter((m) => m != null)
    const row = { day, average: mean(marks) == null ? null : round(mean(marks)), low: marks.length ? round(Math.min(...marks)) : null, high: marks.length ? round(Math.max(...marks)) : null }
    row.band = row.low == null ? null : [row.low, row.high]
    students.forEach((s) => { const p = s.points.find((q) => q.day === day); row[s.name] = p ? round(p.mark) : null })
    return row
  })
  const factorsByDay = days.map((day) => {
    const row = { day }
    for (const f of FACTORS) {
      const scores = students.map((s) => s.points.find((p) => p.day === day)?.factors?.[f.id]?.score).filter((v) => v != null)
      row[f.id] = scores.length ? round(mean(scores) * 100) : null
    }
    return row
  })

  const withChange = students.filter((s) => s.change != null)
  const best = [...withChange].sort((a, b) => b.change - a.change)[0]
  const warnings = []
  for (const s of students) {
    if (s.lastChange != null && s.lastChange <= -10) warnings.push({ id: s.id, name: s.name, kind: 'dropped', text: `${s.name} dropped ${round(-s.lastChange)} points at the last snapshot (${round(s.previous)} to ${round(s.latest)}).` })
    if (s.latest != null && s.latest < 40) warnings.push({ id: s.id, name: s.name, kind: 'low', text: `${s.name} is at ${round(s.latest)}, below 40. Worth a conversation before the sprint ends.` })
    if (s.width != null && s.width >= 40) warnings.push({ id: s.id, name: s.name, kind: 'uncertain', text: `The prediction for ${s.name} is still very uncertain (a range of ${round(s.width)} points). More work in the repository will narrow it.` })
  }

  const firstAvg = chart[0]?.average ?? null
  const latestAvg = chart.at(-1)?.average ?? null
  return {
    students, chart, factorsByDay, warnings, days,
    team: {
      snapshots: days.length, first: firstAvg, latest: latestAvg,
      change: days.length > 1 && firstAvg != null && latestAvg != null ? latestAvg - firstAvg : null,
      lastAt: Math.max(0, ...students.flatMap((s) => s.points.map((p) => p.t))) || null,
      improved: best && best.change >= 5 ? best : null,
      lowCount: students.filter((s) => s.latest != null && s.latest < 40).length,
    },
  }
}

/** How far through the sprint it is: 0 before it starts, 1 once it is over. */
export function sprintProgress(sprint, now = Date.now()) {
  if (!sprint?.start || !sprint?.end) return null
  const start = new Date(`${sprint.start}T00:00:00`).getTime()
  const end = new Date(`${sprint.end}T23:59:59`).getTime()
  if (!(end > start)) return null
  const share = Math.max(0, Math.min(1, (now - start) / (end - start)))
  const days = Math.max(1, Math.round((end - start) / 864e5))
  return { share, days, day: Math.min(days, Math.max(1, Math.ceil(share * days))), over: now > end, notStarted: now < start }
}

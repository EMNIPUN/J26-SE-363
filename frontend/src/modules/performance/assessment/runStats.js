const ACTIVE = ['queued', 'running', 'waiting_human']
const OK = ['succeeded', 'completed', 'finished']
const BAD = ['failed', 'cancelled']

const seconds = (r) => (r.started_at && r.finished_at ? (new Date(r.finished_at) - new Date(r.started_at)) / 1000 : null)

/** What the runs of a team add up to: how many, how many worked, how long they took, and the latest one. `runs` is newest first, as the API sends it. */
export function runStats(runs) {
  const list = runs || []
  const done = list.filter((r) => OK.includes(r.status))
  const failed = list.filter((r) => r.status === 'failed')
  const ended = list.filter((r) => OK.includes(r.status) || BAD.includes(r.status))
  const times = done.map(seconds).filter((s) => s != null)
  const latest = list[0] || null
  const students = list.find((r) => OK.includes(r.status) && r.summary?.students != null)?.summary.students ?? null
  return {
    total: list.length,
    snapshots: list.filter((r) => r.mode !== 'final').length,
    finals: list.filter((r) => r.mode === 'final').length,
    succeeded: done.length,
    failed: failed.length,
    cancelled: list.filter((r) => r.status === 'cancelled').length,
    active: list.filter((r) => ACTIVE.includes(r.status)).length,
    successRate: ended.length ? done.length / ended.length : null,
    averageSeconds: times.length ? times.reduce((a, b) => a + b, 0) / times.length : null,
    fastestSeconds: times.length ? Math.min(...times) : null,
    slowestSeconds: times.length ? Math.max(...times) : null,
    latest,
    students,
    // oldest first, for a chart that reads left to right
    durations: [...list].reverse().map((r, i) => ({ n: i + 1, id: r.id, label: `${r.mode === 'final' ? 'Final' : 'Snapshot'} ${i + 1}`, seconds: seconds(r), status: r.status, mode: r.mode })).filter((d) => d.seconds != null),
  }
}

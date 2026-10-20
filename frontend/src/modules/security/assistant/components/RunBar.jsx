import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import Badge from '@/shared/components/Badge.jsx'
import { MockBadge } from './common.jsx'
import { canPickStudent } from '../hooks/useViewerRole.js'
import { headline, runLabel } from '../lib/format.js'

const ALL = '__team__'

// The bar at the top of every Security Assistant page: which run, whose findings, and the badges that must always be visible.
export default function RunBar({ runs, selection, role, students, overview }) {
  const mine = overview?.my_contributor_ids ?? []
  return (
    <div data-slot="run-bar" className="flex flex-col gap-3 rounded-xl border border-border bg-card p-3 sm:flex-row sm:flex-wrap sm:items-center">
      <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-muted-foreground sm:w-96">
        Run
        <Select value={selection.run ?? ''} onValueChange={selection.setRun}>
          <SelectTrigger aria-label="Run" className="w-full">
            <SelectValue placeholder="Choose a run" />
          </SelectTrigger>
          <SelectContent>
            {runs.map((run) => (
              <SelectItem key={run.run_id} value={run.run_id}>
                {runLabel(run)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </label>

      {canPickStudent(role) ? (
        <label className="flex flex-col gap-1 text-xs font-medium text-muted-foreground sm:w-56">
          Student
          <Select value={selection.student ?? ALL} onValueChange={(value) => selection.setStudent(value === ALL ? null : value)}>
            <SelectTrigger aria-label="Student" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>The whole team</SelectItem>
              {(students ?? []).map((s) => (
                <SelectItem key={s.id} value={s.id}>
                  {s.display_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
      ) : (
        <p className="text-xs text-muted-foreground">
          Showing the team run and your own findings.{' '}
          {mine.length ? (
            <>
              Your contributor id: <span className="font-mono font-semibold text-foreground">{mine.join(', ')}</span>
            </>
          ) : (
            'No contributor id was found for you in this run, so "mine" is empty.'
          )}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2 sm:ml-auto">
        {overview && <Badge tone={overview.run.complete ? 'success' : 'danger'}>{headline(overview.run)}</Badge>}
        <MockBadge>MOCK Tutor</MockBadge>
      </div>
    </div>
  )
}

import { ScanSearch } from 'lucide-react'
import { useParams } from 'react-router-dom'
import PageHeader from '@/shared/components/PageHeader.jsx'
import QueryBoundary from '@/shared/components/QueryBoundary.jsx'
import EmptyState from '@/shared/components/EmptyState.jsx'
import { Button } from '@/components/ui/button'
import { isDemoMode } from '../config.js'
import { canPickStudent, useViewerRole } from '../hooks/useViewerRole.js'
import { useRunOverview, useRuns, useSelection, useStudents } from '../hooks/useSecurityAssistant.js'
import { DemoBanner, HowToRead } from './common.jsx'
import RunBar from './RunBar.jsx'

export const NO_SCAN_REASON =
  'Starting a scan from the browser is not built yet: the Security Assistant is not connected to the orchestrator. Runs are made from the command line and shown here.'

export function StartScanControl() {
  return (
    <div className="flex flex-col items-end gap-1">
      <Button size="sm" variant="outline" disabled title={NO_SCAN_REASON} aria-describedby="no-scan-reason">
        <ScanSearch className="h-4 w-4" /> Start a scan
      </Button>
      <span id="no-scan-reason" className="max-w-xs text-right text-[11px] text-muted-foreground">
        Not available: {NO_SCAN_REASON}
      </span>
    </div>
  )
}

// What every Security Assistant page has in common: header, "how to read this page", the demo label, the run bar and the loading and error states.
export default function AssistantFrame({ title, description, howToRead, children }) {
  const { teamId } = useParams()
  const role = useViewerRole()
  const runsQuery = useRuns(teamId)
  const runs = runsQuery.data?.runs ?? []
  const selection = useSelection(runs)
  const studentsQuery = useStudents(teamId, canPickStudent(role))
  const overviewQuery = useRunOverview(teamId, selection.run, selection.student)
  const demo = isDemoMode() || Boolean(runsQuery.data?.demo_data)

  return (
    <div className="space-y-4 animate-fade-rise">
      <PageHeader title={title} description={description} actions={<StartScanControl />} />
      <DemoBanner active={demo} />
      <HowToRead>{howToRead}</HowToRead>
      <QueryBoundary query={runsQuery} variant="card" count={2}>
        {() =>
          runs.length ? (
            <>
              <RunBar runs={runs} selection={selection} role={role} students={studentsQuery.data} overview={overviewQuery.data} />
              <QueryBoundary query={overviewQuery} variant="card" count={3}>
                {(overview) => children({ overview, selection, team: teamId, role })}
              </QueryBoundary>
            </>
          ) : (
            <EmptyState
              title="No Security Assistant runs for this team yet"
              description="A run appears here after the assessment has been run on the team's repository and its result folder has been added. Nothing is shown in its place."
            />
          )
        }
      </QueryBoundary>
    </div>
  )
}

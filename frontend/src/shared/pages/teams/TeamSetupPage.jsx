import { Navigate, useParams } from 'react-router-dom'
import { Skeleton } from '@/components/ui/skeleton'
import { useTeam } from '../../hooks/useTeams.js'
import NotFound from '../NotFound.jsx'
import TeamSetupWizard from './TeamSetupWizard.jsx'

/**
 * /teams/new starts a team; /teams/new/:code carries on with one that is still pending.
 * A team that is already set up goes to its members page instead (that is where the person lands
 * after the last step).
 */
export default function TeamSetupPage() {
  const { code } = useParams()
  const team = useTeam(code)

  if (!code) return <TeamSetupWizard key="new" />
  if (team.isPending) return <Skeleton className="mx-auto h-64 w-full max-w-2xl" aria-busy="true" />
  if (team.isError) return <NotFound />
  if (team.data.status !== 'pending') return <Navigate to={`/teams/${team.data.code}/members`} replace />
  return <TeamSetupWizard key={team.data.id} team={team.data} />
}

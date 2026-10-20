import { useEffect } from 'react'
import { useParams, Outlet, Navigate } from 'react-router-dom'
import { useMyTeams } from '../hooks/useTeams.js'
import { useAuth } from '../auth/useAuth.js'
import TeamAccessGate from '../github/TeamAccessGate.jsx'
import { rememberTeam } from '../utils/recentTeams.js'
import { teamHref } from '../utils/teams.js'
import { useScope } from '../context/useScope.js'
import NotFound from '../pages/NotFound.jsx'

/**
 * Guards /teams/:teamId/*: the team must be one the person belongs to. Anything else (a typo,
 * someone else's team) is "not found", and the page never falls back to a different team.
 */
export default function TeamScopeGuard() {
  const { teamId } = useParams()
  const { user } = useAuth()
  const { groups, selectedGroupId, setGroupId, isLoading } = useScope()
  const teams = useMyTeams()
  const pending = teams.data?.find(
    (t) => t.status === 'pending' && (t.code.toLowerCase() === teamId?.toLowerCase() || t.id === teamId),
  )

  const matchedGroup = groups.find(
    (g) => g.code?.toLowerCase() === teamId?.toLowerCase() || g.id === teamId,
  )

  // Keep the active team in step with the address.
  useEffect(() => {
    if (matchedGroup && selectedGroupId !== matchedGroup.id) setGroupId(matchedGroup.id)
  }, [matchedGroup, selectedGroupId, setGroupId])

  // Remember it for the "Recently opened" row on the home page.
  useEffect(() => {
    if (matchedGroup?.code) rememberTeam(matchedGroup.code)
  }, [matchedGroup?.code])

  if (isLoading) return <div className="min-h-[40svh]" />
  if (pending) return <Navigate to={teamHref(pending)} replace /> // finish the setup first
  if (!matchedGroup) return <NotFound />
  // A student enters the team only through the GitHub gate (checked live on every load); lecturers and administrators supervise and go straight in.
  if (user?.role === 'student') {
    return (
      <TeamAccessGate teamId={matchedGroup.code}>
        <Outlet />
      </TeamAccessGate>
    )
  }
  return <Outlet />
}

import { useEffect } from 'react'
import { useParams, Outlet, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useMyTeams } from '../hooks/useTeams.js'
import { useAuth } from '../auth/useAuth.js'
import { accessHref, forgetPassed, hasPassed } from '../github/accessPassed.js'
import { githubService } from '../github/githubService.js'
import { rememberTeam } from '../utils/recentTeams.js'
import { teamHref } from '../utils/teams.js'
import { useScope } from '../context/useScope.js'
import NotFound from '../pages/NotFound.jsx'

/** Once inside, asks again every few minutes and when the tab is used again: if access was taken away on GitHub, the person goes back to the access page. */
function GateWatch({ who, team }) {
  const navigate = useNavigate()
  const location = useLocation()
  const watch = useQuery({
    queryKey: ['github', 'gate-watch', team], queryFn: () => githubService.gate(team),
    initialData: { state: 'ok' }, staleTime: 5 * 60 * 1000, refetchInterval: 5 * 60 * 1000, refetchOnWindowFocus: true, gcTime: 0, retry: 0,
  })
  const state = watch.data?.state
  useEffect(() => {
    if (state && state !== 'ok') {
      forgetPassed(who, team)
      navigate(accessHref(team, location.pathname + location.search), { replace: true })
    }
  }, [state, who, team, navigate, location.pathname, location.search])
  return null
}

/**
 * Guards /teams/:teamId/*: the team must be one the person belongs to. Anything else (a typo,
 * someone else's team) is "not found", and the page never falls back to a different team.
 */
export default function TeamScopeGuard() {
  const { teamId } = useParams()
  const location = useLocation()
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
  // A lecturer or administrator who is already known to be one goes straight in. Everyone else, including while the role is still loading, is sent to the team's access page
  // first and enters only once it has passed (in this page load; a reload checks again). The dashboard is never drawn before that.
  if (user?.role !== 'instructor' && user?.role !== 'admin') {
    const who = user?.email || 'me'
    if (!hasPassed(who, matchedGroup.code)) return <Navigate to={accessHref(matchedGroup.code, location.pathname + location.search)} replace />
    return (
      <>
        <GateWatch who={who} team={matchedGroup.code} />
        <Outlet />
      </>
    )
  }
  return <Outlet />
}

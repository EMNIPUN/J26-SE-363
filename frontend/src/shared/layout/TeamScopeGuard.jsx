import { useEffect } from 'react'
import { useParams, Outlet } from 'react-router-dom'
import { useScope } from '../context/useScope.js'
import NotFound from '../pages/NotFound.jsx'

/**
 * Guards /teams/:teamId/*: the team must be one the person belongs to. Anything else (a typo,
 * someone else's team) is "not found", and the page never falls back to a different team.
 */
export default function TeamScopeGuard() {
  const { teamId } = useParams()
  const { groups, selectedGroupId, setGroupId, isLoading } = useScope()

  const matchedGroup = groups.find(
    (g) => g.code?.toLowerCase() === teamId?.toLowerCase() || g.id === teamId,
  )

  // Keep the active team in step with the address.
  useEffect(() => {
    if (matchedGroup && selectedGroupId !== matchedGroup.id) setGroupId(matchedGroup.id)
  }, [matchedGroup, selectedGroupId, setGroupId])

  if (isLoading) return <div className="min-h-[40svh]" />
  if (!matchedGroup) return <NotFound />
  return <Outlet />
}

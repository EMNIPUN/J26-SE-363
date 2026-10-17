import { useEffect } from 'react'
import { useParams, Outlet, Navigate, useLocation } from 'react-router-dom'
import { useScope } from '../context/useScope.js'
import { GROUPS } from '../constants/academicScope.js'

export default function TeamScopeGuard() {
  const { teamId } = useParams()
  const location = useLocation()
  const { selectedGroup, setGroupId } = useScope()

  // Match teamId from URL against GROUPS by code or id (case-insensitive)
  const matchedGroup = GROUPS.find(
    (g) =>
      g.code?.toLowerCase() === teamId?.toLowerCase() ||
      g.id?.toLowerCase() === teamId?.toLowerCase(),
  )

  // Synchronize ScopeContext with URL when valid
  useEffect(() => {
    if (matchedGroup && selectedGroup?.id !== matchedGroup.id) {
      setGroupId(matchedGroup.id)
    }
  }, [matchedGroup, selectedGroup, setGroupId])

  // Fallback: If teamId in URL does not exist in registry, redirect to the active team.
  if (!matchedGroup) {
    const targetCode = selectedGroup?.code || GROUPS[0].code
    const safePath = location.pathname.replace(teamId, targetCode)
    return <Navigate to={safePath} replace />
  }

  return <Outlet />
}

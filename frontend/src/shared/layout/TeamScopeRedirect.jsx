import { Navigate, useLocation } from 'react-router-dom'
import { useScope } from '../context/useScope.js'

/**
 * Backward-compatibility redirector:
 * Redirects unscoped paths (e.g. /performance/dashboard or /app) to their team-scoped
 * equivalent (/teams/:teamId/performance/dashboard). A person with no team goes to the home page.
 */
export default function TeamScopeRedirect() {
  const location = useLocation()
  const { selectedGroup, isLoading } = useScope()

  if (isLoading) return <div className="min-h-[40svh]" />
  if (!selectedGroup) return <Navigate to="/home" replace />
  return (
    <Navigate to={`/teams/${selectedGroup.code}${location.pathname}${location.search}`} replace />
  )
}

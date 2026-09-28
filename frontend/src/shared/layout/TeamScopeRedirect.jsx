import { Navigate, useLocation } from 'react-router-dom'
import { useScope } from '../context/useScope.js'

/**
 * Backward-compatibility redirector:
 * Redirects unscoped paths (e.g. /performance/dashboard or /app)
 * to their team-scoped equivalent (/teams/:teamId/performance/dashboard or /teams/:teamId/app).
 */
export default function TeamScopeRedirect() {
  const location = useLocation()
  const { selectedGroup } = useScope()
  const activeTeamCode = selectedGroup?.code || 'J26-SE-363'

  // Prepend /teams/:teamCode to the path
  const targetPath = `/teams/${activeTeamCode}${location.pathname}${location.search}`
  return <Navigate to={targetPath} replace />
}

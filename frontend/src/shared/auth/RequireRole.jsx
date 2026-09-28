import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './useAuth.js'
import Unauthorized from '../pages/Unauthorized.jsx'

/**
 * Route guard that restricts sub-routes to users with specific roles.
 *
 * @param {Object} props
 * @param {string[]} props.allowedRoles - Array of allowed role names (e.g. ['admin'], ['instructor', 'admin'])
 * @param {'forbidden' | 'redirect'} [props.fallback='forbidden'] - Action on unauthorized access: show 403 page or redirect to /app
 */
export default function RequireRole({ allowedRoles = [], fallback = 'forbidden' }) {
  const { user, isInitialized, isLoggingOut } = useAuth()

  if (!isInitialized || isLoggingOut) {
    return <div className="min-h-screen bg-background" />
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  const isAllowed = allowedRoles.length === 0 || allowedRoles.includes(user.role)

  if (!isAllowed) {
    if (fallback === 'redirect') {
      return <Navigate to="/app" replace />
    }
    return <Unauthorized allowedRoles={allowedRoles} />
  }

  return <Outlet />
}

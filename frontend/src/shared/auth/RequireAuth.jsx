import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './useAuth.js'

export default function RequireAuth() {
  const { user, isInitialized, isLoggingOut } = useAuth()

  if (!isInitialized || isLoggingOut) {
    return <div className="min-h-screen bg-background" />
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}

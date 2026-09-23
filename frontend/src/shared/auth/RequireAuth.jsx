import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './useAuth.js'

export default function RequireAuth() {
  const { user, isInitialized } = useAuth()

  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="h-6 w-6 rounded-full border-2 border-primary border-t-transparent animate-spin" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}

import PropTypes from 'prop-types'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import SelviaLogo from '../components/SelviaLogo.jsx'
import { useAuth } from './useAuth.js'
import { rememberReturnTo, takeReturnTo } from './returnTo.js'

function AccountUnavailable({ onRetry, onSignOut }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-background px-4">
      <SelviaLogo size={36} showText showTagline={false} />
      <Card className="w-full max-w-sm gap-4 p-6 text-center">
        <h1 className="text-lg font-semibold text-foreground">We cannot reach SELVIA</h1>
        <p className="text-sm text-muted-foreground">
          Your account could not be loaded. Check your connection and try again.
        </p>
        <div className="flex flex-col gap-2">
          <Button onClick={onRetry}>Try again</Button>
          <Button variant="ghost" onClick={onSignOut}>
            Sign out
          </Button>
        </div>
      </Card>
    </div>
  )
}

AccountUnavailable.propTypes = {
  onRetry: PropTypes.func.isRequired,
  onSignOut: PropTypes.func.isRequired,
}

/**
 * Sits after RequireAuth. Waits for the account, and sends people who have not finished
 * onboarding to /onboarding (and finished ones away from it).
 */
export default function RequireAccount({ onboarding = false }) {
  const { user, accountStatus, isInitialized, isLoggingOut, refreshAccount, logout } = useAuth()
  const location = useLocation()

  if (!isInitialized || isLoggingOut) return <div className="min-h-screen bg-background" />
  if (!user) return <Navigate to="/login" replace />
  if (accountStatus === 'error') {
    return <AccountUnavailable onRetry={refreshAccount} onSignOut={logout} />
  }

  if (onboarding) {
    return user.onboarded ? <Navigate to={takeReturnTo() ?? '/home'} replace /> : <Outlet />
  }
  if (!user.onboarded) {
    rememberReturnTo(`${location.pathname}${location.search}`)
    return <Navigate to="/onboarding" replace />
  }
  return <Outlet />
}

RequireAccount.propTypes = {
  onboarding: PropTypes.bool,
}

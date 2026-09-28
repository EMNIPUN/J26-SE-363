import { Link } from 'react-router-dom'
import { ShieldAlert, ArrowLeft, LayoutDashboard } from 'lucide-react'
import { useAuth } from '../auth/useAuth.js'
import { Button } from '@/components/ui/button'

export default function Unauthorized({ allowedRoles = [] }) {
  const { user } = useAuth()

  const roleLabels = {
    admin: 'Administrator',
    instructor: 'Instructor',
    student: 'Student',
  }

  const formattedRequired = allowedRoles.length > 0
    ? allowedRoles.map((r) => roleLabels[r] || r).join(' or ')
    : 'Elevated'

  const currentRoleLabel = user?.role ? roleLabels[user.role] || user.role : 'Guest'

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center px-4 py-12 text-center animate-fade-rise">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 text-destructive mb-6 ring-8 ring-destructive/5">
        <ShieldAlert className="h-8 w-8" strokeWidth={2} />
      </div>

      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-destructive/10 text-destructive mb-3">
        <span>403 Forbidden</span>
      </div>

      <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground mb-2">
        Access Restricted
      </h1>

      <p className="text-sm sm:text-base text-muted-foreground max-w-md mx-auto mb-6">
        You do not have permission to view this section. This area requires{' '}
        <span className="font-semibold text-foreground">{formattedRequired}</span> privileges.
      </p>

      {user && (
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted text-xs text-muted-foreground mb-8 border border-border">
          <span>Current Account:</span>
          <span className="font-semibold text-foreground">{user.name || user.email}</span>
          <span className="text-muted-foreground/60">•</span>
          <span className="capitalize font-medium text-foreground">{currentRoleLabel}</span>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-center gap-3">
        <Button asChild size="default" className="gap-2">
          <Link to="/app">
            <LayoutDashboard className="h-4 w-4" />
            Return to Dashboard
          </Link>
        </Button>
        <Button asChild variant="outline" size="default" className="gap-2">
          <Link to={-1}>
            <ArrowLeft className="h-4 w-4" />
            Go Back
          </Link>
        </Button>
      </div>
    </div>
  )
}

import { NavLink, Outlet } from 'react-router-dom'
import { LogOut, ShieldCheck, UserRound, UsersRound } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useAuth } from '../../auth/useAuth.js'

const TABS = [
  { to: '/profile', label: 'Profile', icon: UserRound, end: true },
  { to: '/profile/security', label: 'Security', icon: ShieldCheck },
  { to: '/profile/teams', label: 'Teams', icon: UsersRound },
]

/**
 * The account area: a menu on the left (a row of tabs on a phone) and the chosen tab beside it.
 * Opened from the picture in the top bar.
 */
export default function ProfileLayout() {
  const { logout, isLoggingOut } = useAuth()

  return (
    <div className="grid gap-6 lg:grid-cols-[14rem_minmax(0,1fr)] lg:gap-10">
      <aside className="lg:sticky lg:top-20 lg:self-start">
        <nav aria-label="Account" className="flex gap-1 overflow-x-auto lg:flex-col lg:overflow-visible">
          {TABS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring',
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground',
                )
              }
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-2 border-t border-border pt-2">
          <Button
            variant="ghost"
            className="w-full justify-start gap-2.5 px-3 text-destructive hover:text-destructive"
            loading={isLoggingOut}
            onClick={logout}
          >
            <LogOut aria-hidden="true" />
            Sign out
          </Button>
        </div>
      </aside>

      <div className="min-w-0 max-w-2xl">
        <Outlet />
      </div>
    </div>
  )
}

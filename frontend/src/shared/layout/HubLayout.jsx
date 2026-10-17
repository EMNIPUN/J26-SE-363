import { Link, NavLink, Outlet } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useAuth } from '../auth/useAuth.js'
import Avatar from '../components/Avatar.jsx'
import SelviaLogo from '../components/SelviaLogo.jsx'
import ThemeToggle from '../components/ThemeToggle.jsx'
import HubNav, { HubMenu } from './HubNav.jsx'
import HubNotifications from './HubNotifications.jsx'

/**
 * Frame for the pages that come before a team's workspace: home, the team list, creating a team,
 * invitations and the account area (the picture in the bar opens it). Inside a team the person uses DashboardShell instead.
 * The bar has three parts: the brand, the navigation in the middle, and the person's own controls.
 */
export default function HubLayout() {
  const { user } = useAuth()
  const canCreate = user?.role === 'instructor'

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-30 border-b border-sidebar-border bg-sidebar/95 backdrop-blur">
        <div className="mx-auto grid h-14 w-full max-w-[96rem] grid-cols-[1fr_auto] md:grid-cols-[1fr_auto_1fr] items-center px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2 justify-self-start">
            <HubMenu />
            <Link
              to="/home"
              aria-label="SELVIA home"
              className="rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <SelviaLogo size={28} showText showTagline={false} />
            </Link>
          </div>

          <HubNav canCreate={canCreate} />

          <div className="flex items-center gap-1.5 justify-self-end">
            <HubNotifications />
            <ThemeToggle />
            <NavLink
              to="/profile"
              aria-label="Your profile"
              className={({ isActive }) =>
                cn(
                  'flex h-9 w-9 items-center justify-center rounded-full outline-none transition-shadow focus-visible:ring-2 focus-visible:ring-ring',
                  isActive ? 'ring-2 ring-primary' : 'hover:ring-2 hover:ring-border',
                )
              }
            >
              <Avatar name={user?.name} picture={user?.picture} size={32} />
            </NavLink>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[96rem] px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  )
}

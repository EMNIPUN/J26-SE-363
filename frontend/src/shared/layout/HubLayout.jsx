import { Link, Outlet } from 'react-router-dom'
import { LogOut, UserRound } from 'lucide-react'
import { useAuth } from '../auth/useAuth.js'
import { getRoleLabel } from '../constants/roles.js'
import Avatar from '../components/Avatar.jsx'
import SelviaLogo from '../components/SelviaLogo.jsx'
import ThemeToggle from '../components/ThemeToggle.jsx'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

/**
 * Frame for the pages that come before a team's workspace: the team list, creating a team,
 * invitations and the profile. Inside a team the person uses DashboardShell instead.
 */
export default function HubLayout() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-30 border-b border-sidebar-border bg-sidebar/95 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link
            to="/home"
            aria-label="SELVIA home"
            className="rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <SelviaLogo size={28} showText showTagline={false} />
          </Link>

          <div className="flex items-center gap-1.5">
            <ThemeToggle />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  aria-label="Account menu"
                  className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-full outline-none hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <Avatar name={user?.name} size={32} />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64">
                <DropdownMenuLabel className="font-normal">
                  <p className="truncate text-sm font-semibold text-foreground">{user?.name}</p>
                  {user?.email && (
                    <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                  )}
                  <p className="mt-1 text-xs text-muted-foreground">{getRoleLabel(user?.role)}</p>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild className="cursor-pointer">
                  <Link to="/profile">
                    <UserRound className="mr-2 h-4 w-4" />
                    Profile
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={logout}
                  className="cursor-pointer text-destructive focus:text-destructive"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>
    </div>
  )
}

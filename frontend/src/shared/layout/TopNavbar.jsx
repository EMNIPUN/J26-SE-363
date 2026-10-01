import { useState } from 'react'
import { Search, LogOut, Menu } from 'lucide-react'
import { useAuth } from '../auth/useAuth.js'
import { getRoleLabel } from '../constants/roles.js'
import Avatar from '../components/Avatar.jsx'
import ThemeToggle from '../components/ThemeToggle.jsx'
import NotificationDropdown from '../components/NotificationDropdown.jsx'
import CommandPalette from '../components/CommandPalette.jsx'
import SelviaLogo from '../components/SelviaLogo.jsx'
import ScopeSelector from '../components/ScopeSelector.jsx'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button as ShadcnButton } from '@/components/ui/button'

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)

export default function TopNavbar({ onToggleMobileMenu, sidebarCollapsed = false }) {
  const [commandOpen, setCommandOpen] = useState(false)
  const { user, logout } = useAuth()

  return (
    <header className="sticky top-0 z-40 flex h-16 w-full items-center border-b border-topbar-border bg-topbar/95 text-topbar-foreground px-0 backdrop-blur shadow-2xs">
      <div
        className={`flex h-full items-center gap-3 px-4 sm:px-6 lg:shrink-0 lg:overflow-hidden transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
          sidebarCollapsed ? 'lg:w-[68px] lg:px-3' : 'lg:w-64'
        }`}
      >
        {onToggleMobileMenu && (
          <ShadcnButton
            variant="ghost"
            size="icon"
            className="lg:hidden h-9 w-9 cursor-pointer"
            onClick={onToggleMobileMenu}
            aria-label="Open navigation"
          >
            <Menu className="h-5 w-5" />
          </ShadcnButton>
        )}

        <SelviaLogo size={32} showText={!sidebarCollapsed} />
      </div>

      <div className="h-5 w-px bg-border/60 hidden xl:block" />

      <div className="hidden xl:flex items-center flex-1 max-w-md ml-4">
        <button
          type="button"
          onClick={() => setCommandOpen(true)}
          className="relative w-full flex items-center justify-between gap-3 h-9 px-3 rounded-lg border border-border bg-background hover:bg-muted/60 text-xs text-muted-foreground transition-all duration-150 cursor-pointer text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="flex items-center gap-2 min-w-0">
            <Search className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate whitespace-nowrap">Search pages and actions…</span>
          </span>
          <kbd className="inline-flex shrink-0 items-center gap-0.5 rounded border border-border bg-muted/60 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground shadow-2xs">
            {isMac ? '⌘' : 'Ctrl'} K
          </kbd>
        </button>
      </div>

      <div className="flex min-w-0 items-center gap-1.5 sm:gap-2 ml-auto pr-4 sm:pr-6">
        <ShadcnButton
          variant="ghost"
          size="icon"
          className="xl:hidden h-9 w-9 text-muted-foreground hover:text-foreground cursor-pointer"
          onClick={() => setCommandOpen(true)}
          aria-label="Search pages and actions"
        >
          <Search className="h-4 w-4" />
        </ShadcnButton>

        <div className="hidden sm:block min-w-0">
          <ScopeSelector />
        </div>

        <ThemeToggle />

        <NotificationDropdown />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="flex h-9 w-9 items-center justify-center rounded-full hover:bg-muted/60 transition-all duration-150 active:scale-[0.98] cursor-pointer outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Account menu"
            >
              <Avatar name={user?.name} size={32} />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64 animate-scale-in">
            <DropdownMenuLabel className="font-normal">
              <div className="flex items-center gap-3 py-1">
                <Avatar name={user?.name} size={36} />
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-foreground">{user?.name}</p>
                  {user?.email && (
                    <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                  )}
                  <span className="mt-1 inline-flex items-center rounded-md bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
                    {getRoleLabel(user?.role)}
                  </span>
                </div>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={logout}
              className="text-destructive focus:text-destructive cursor-pointer"
            >
              <LogOut className="mr-2 h-4 w-4" />
              <span>Sign out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} />
    </header>
  )
}

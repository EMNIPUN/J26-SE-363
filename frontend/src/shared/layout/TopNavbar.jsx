import { useState } from 'react'
import { Search, LogOut, Menu, UserRound } from 'lucide-react'
import { useAuth } from '../auth/useAuth.js'
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button as ShadcnButton } from '@/components/ui/button'

export default function TopNavbar({ onToggleMobileMenu, sidebarCollapsed = false }) {
  const [commandOpen, setCommandOpen] = useState(false)
  const { user, logout } = useAuth()

  function handleLogout() {
    logout()
  }

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
            aria-label="Toggle navigation"
          >
            <Menu className="h-5 w-5" />
          </ShadcnButton>
        )}

        <SelviaLogo size={32} showText={!sidebarCollapsed} />
      </div>

      <div className="h-5 w-px bg-border/60 hidden sm:block" />

      <div className="hidden md:flex items-center flex-1 max-w-lg ml-3">
        <button
          type="button"
          onClick={() => setCommandOpen(true)}
          className="relative w-full flex items-center justify-between h-9 px-3 rounded-lg border border-border bg-background hover:bg-muted/60 text-xs text-muted-foreground transition-all duration-150 cursor-pointer text-left"
        >
          <div className="flex items-center gap-2">
            <Search className="h-3.5 w-3.5" />
            <span>Search portals, projects, actions...</span>
          </div>
          <kbd className="inline-flex items-center gap-0.5 rounded border border-border bg-muted/60 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground shadow-2xs">
            <span className="text-[11px]">⌘</span>K
          </kbd>
        </button>
      </div>

      <div className="flex min-w-0 items-center gap-2 ml-auto pr-4 sm:pr-6">
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
              aria-label="User account menu"
            >
              <Avatar name={user?.name} size={32} />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-44 animate-scale-in">
            <DropdownMenuItem className="cursor-pointer">
              <UserRound className="mr-2 h-4 w-4" />
              <span>Profile</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout} className="text-destructive focus:text-destructive cursor-pointer">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} />
    </header>
  )
}


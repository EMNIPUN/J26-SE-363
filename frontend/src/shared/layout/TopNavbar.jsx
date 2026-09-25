import { useState } from 'react'
import { Search, LogOut, Menu, ChevronDown } from 'lucide-react'
import { useAuth } from '../auth/useAuth.js'
import Avatar from '../components/Avatar.jsx'
import ThemeToggle from '../components/ThemeToggle.jsx'
import NotificationDropdown from '../components/NotificationDropdown.jsx'
import CommandPalette from '../components/CommandPalette.jsx'
import MentorLogo from '../components/MentorLogo.jsx'
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

export default function TopNavbar({ onToggleMobileMenu }) {
  const [commandOpen, setCommandOpen] = useState(false)
  const { user, logout } = useAuth()

  function handleLogout() {
    logout()
  }

  return (
    <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-topbar-border bg-topbar/95 text-topbar-foreground px-4 sm:px-6 backdrop-blur shadow-2xs">
      <div className="flex items-center gap-3">
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

        <MentorLogo size={32} showText={true} />
        <div className="h-5 w-px bg-border/60 mx-1.5 hidden sm:block" />
        <ScopeSelector />
      </div>

      <div className="hidden md:flex items-center flex-1 max-w-md mx-6">
        <button
          type="button"
          onClick={() => setCommandOpen(true)}
          className="relative w-full flex items-center justify-between h-9 px-3 rounded-lg border border-border bg-card/85 hover:bg-card text-xs text-muted-foreground transition-all duration-150 cursor-pointer text-left shadow-2xs"
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

      <div className="flex items-center gap-2">
        <ThemeToggle />

        <NotificationDropdown />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="flex items-center gap-2 rounded-full p-1 pl-1.5 pr-2.5 hover:bg-muted/60 transition-all duration-150 active:scale-[0.98] cursor-pointer outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring group"
              aria-label="User account menu"
            >
              <Avatar name={user?.name} size={32} />
              <div className="hidden sm:flex flex-col items-start text-left text-xs leading-tight">
                <span className="font-semibold text-foreground">{user?.name}</span>
                <span className="text-muted-foreground capitalize text-[11px]">{user?.role}</span>
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground group-hover:text-foreground transition-colors duration-150" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56 animate-scale-in">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">{user?.name}</p>
                <p className="text-xs leading-none text-muted-foreground">{user?.email}</p>
              </div>
            </DropdownMenuLabel>
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


import { useNavigate } from 'react-router-dom'
import { GraduationCap, Search, Bell, LogOut, Menu } from 'lucide-react'
import { useAuth } from '../auth/useAuth.js'
import Avatar from '../components/Avatar.jsx'
import Badge from '../components/Badge.jsx'
import ThemeToggle from '../components/ThemeToggle.jsx'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Button as ShadcnButton } from '@/components/ui/button'

const ROLE_TONE = { student: 'primary', instructor: 'success', admin: 'warning' }

export default function TopNavbar({ onToggleMobileMenu }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-border bg-card/95 px-4 sm:px-6 backdrop-blur">
      <div className="flex items-center gap-3">
        {onToggleMobileMenu && (
          <ShadcnButton
            variant="ghost"
            size="icon"
            className="md:hidden h-9 w-9"
            onClick={onToggleMobileMenu}
            aria-label="Toggle navigation"
          >
            <Menu className="h-5 w-5" />
          </ShadcnButton>
        )}

        <div className="flex items-center gap-2 font-bold text-foreground">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
            <GraduationCap className="h-5 w-5" />
          </div>
          <span className="text-lg tracking-tight font-semibold">EduFlow</span>
        </div>
      </div>

      <div className="hidden md:flex items-center flex-1 max-w-md mx-6">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search projects, students, requirements..."
            className="pl-9 h-9 bg-muted/40 text-sm"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <ThemeToggle />

        <ShadcnButton
          variant="ghost"
          size="icon"
          className="relative h-9 w-9 text-muted-foreground hover:text-foreground"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-primary" />
        </ShadcnButton>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="flex items-center gap-2.5 rounded-full p-1 pl-1.5 hover:bg-muted/60 transition-all duration-150 active:scale-[0.98] cursor-pointer outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Avatar name={user?.name} size={32} />
              <div className="hidden sm:flex flex-col items-start text-left text-xs leading-tight mr-1">
                <span className="font-semibold text-foreground">{user?.name}</span>
                <span className="text-muted-foreground capitalize text-[11px]">{user?.role}</span>
              </div>
              <Badge tone={ROLE_TONE[user?.role] ?? 'neutral'} className="hidden sm:inline-flex capitalize">
                {user?.role}
              </Badge>
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
    </header>
  )
}


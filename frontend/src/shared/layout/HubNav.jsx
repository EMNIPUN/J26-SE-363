import PropTypes from 'prop-types'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { ChevronDown, Menu, Plus } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useMyInvitations, useMyTeams } from '../hooks/useTeams.js'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

const RECENT_TEAMS = 5

// One look for every item in the bar: the active one gets a line under it.
const itemClass = (active) =>
  cn(
    'relative flex h-14 cursor-pointer items-center gap-1.5 px-3 text-sm font-medium outline-none transition-colors focus-visible:bg-muted/60',
    active
      ? 'text-foreground after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:rounded-full after:bg-primary'
      : 'text-muted-foreground hover:text-foreground',
  )

function Count({ value }) {
  if (!value) return null
  return (
    <span className="rounded-full bg-primary px-1.5 text-[11px] leading-5 text-primary-foreground">
      {value}
    </span>
  )
}

Count.propTypes = { value: PropTypes.number }

/** "Teams" opens a short list to jump straight into a team, with links to all teams and, for lecturers, a new one. */
function TeamsMenu({ canCreate }) {
  const { pathname } = useLocation()
  const teams = useMyTeams().data ?? []

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button type="button" className={itemClass(pathname.startsWith('/teams'))}>
          Teams
          <ChevronDown className="h-3.5 w-3.5 opacity-60" aria-hidden="true" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="center" className="w-72">
        <DropdownMenuLabel className="text-xs font-medium text-muted-foreground">
          Your teams
        </DropdownMenuLabel>
        {teams.length === 0 && (
          <DropdownMenuItem disabled>No teams yet</DropdownMenuItem>
        )}
        {teams.slice(0, RECENT_TEAMS).map((team) => (
          <DropdownMenuItem key={team.id} asChild className="cursor-pointer">
            <Link to={`/teams/${team.code}`} className="flex items-center justify-between gap-3">
              <span className="truncate">{team.name}</span>
              <span className="font-mono text-xs text-muted-foreground">{team.code}</span>
            </Link>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild className="cursor-pointer">
          <Link to="/teams">All teams</Link>
        </DropdownMenuItem>
        {canCreate && (
          <DropdownMenuItem asChild className="cursor-pointer">
            <Link to="/teams/new">
              <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
              Create team
            </Link>
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

TeamsMenu.propTypes = { canCreate: PropTypes.bool.isRequired }

/** The centre of the top bar: Home, Teams (a menu) and Invitations. Phones use HubMenu instead. */
export default function HubNav({ canCreate }) {
  const waiting = useMyInvitations().data?.length ?? 0

  return (
    <nav aria-label="Main" className="hidden items-center md:flex">
      <NavLink to="/home" className={({ isActive }) => itemClass(isActive)}>
        Home
      </NavLink>
      <TeamsMenu canCreate={canCreate} />
      <NavLink to="/invitations" className={({ isActive }) => itemClass(isActive)}>
        Invitations
        <Count value={waiting} />
      </NavLink>
    </nav>
  )
}

HubNav.propTypes = { canCreate: PropTypes.bool.isRequired }

/** The same links behind one button, for narrow screens. */
export function HubMenu() {
  const waiting = useMyInvitations().data?.length ?? 0

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label="Menu"
          className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-md outline-none hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring md:hidden"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-48">
        <DropdownMenuItem asChild className="cursor-pointer">
          <Link to="/home">Home</Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild className="cursor-pointer">
          <Link to="/teams">Teams</Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild className="cursor-pointer">
          <Link to="/invitations" className="flex items-center justify-between">
            Invitations
            <Count value={waiting} />
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

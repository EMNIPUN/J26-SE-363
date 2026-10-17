import { useMemo } from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { History } from 'lucide-react'
import { readRecentTeams } from '../../utils/recentTeams.js'
import { teamHref } from '../../utils/teams.js'

/** The teams opened last, for one-click return. Not shown when there is only one team to open. */
export default function RecentTeams({ teams }) {
  const recent = useMemo(() => {
    const open = teams.filter((team) => team.status !== 'pending')
    if (open.length < 2) return []
    return readRecentTeams()
      .map((code) => open.find((team) => team.code === code))
      .filter(Boolean)
  }, [teams])

  if (recent.length === 0) return null
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="flex items-center gap-1.5 text-muted-foreground">
        <History className="h-4 w-4" aria-hidden="true" />
        Recently opened
      </span>
      {recent.map((team) => (
        <Link
          key={team.id}
          to={teamHref(team)}
          className="rounded-full border border-border bg-card px-3 py-1 font-medium text-foreground outline-none transition-colors hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring"
        >
          {team.name}
        </Link>
      ))}
    </div>
  )
}

RecentTeams.propTypes = { teams: PropTypes.arrayOf(PropTypes.object).isRequired }

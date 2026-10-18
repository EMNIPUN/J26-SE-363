import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { teamHref } from '../../utils/teams.js'

/** Teams a lecturer started and has not finished, with a way back into the setup. */
export default function DraftTeams({ teams }) {
  if (teams.length === 0) return null
  return (
    <Card className="gap-0 border-amber-300/60 p-0 dark:border-amber-500/30">
      <h2 className="border-b border-border px-4 py-3 text-sm font-semibold text-foreground">
        Finish setting up <span className="font-normal text-muted-foreground">({teams.length})</span>
      </h2>
      <ul className="divide-y divide-border">
        {teams.map((team) => (
          <li key={team.id} className="flex items-center gap-3 px-4 py-2.5">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-foreground">{team.name}</p>
              <p className="truncate text-xs text-muted-foreground">
                {[team.term, team.project?.title ?? 'No project yet'].filter(Boolean).join(' · ')}
              </p>
            </div>
            <Button asChild size="sm" variant="outline">
              <Link to={teamHref(team)}>Continue setup</Link>
            </Button>
          </li>
        ))}
      </ul>
    </Card>
  )
}

DraftTeams.propTypes = { teams: PropTypes.arrayOf(PropTypes.object).isRequired }

import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { AlertCircle } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { needsAttention } from '../../utils/teams.js'

/** Teams with something unfinished: no repository, no leader, invitations still unanswered. */
export default function NeedsAttention({ teams, isStaff }) {
  const items = needsAttention(teams, isStaff)
  if (items.length === 0) return null

  return (
    <Card className="gap-0 p-0">
      <h2 className="border-b border-border px-4 py-3 text-sm font-semibold text-foreground">
        Needs attention <span className="font-normal text-muted-foreground">({items.length})</span>
      </h2>
      <ul className="divide-y divide-border">
        {items.map(({ key, team, message }) => (
          <li key={key}>
            <Link
              to={`/teams/${team.code}`}
              className="flex items-center gap-3 px-4 py-2.5 text-sm outline-none hover:bg-muted/40 focus-visible:bg-muted/40"
            >
              <AlertCircle className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />
              <span className="min-w-0 flex-1 truncate">
                <span className="font-medium text-foreground">{team.name}</span>{' '}
                <span className="text-muted-foreground">{message}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  )
}

NeedsAttention.propTypes = {
  teams: PropTypes.arrayOf(PropTypes.object).isRequired,
  isStaff: PropTypes.bool.isRequired,
}

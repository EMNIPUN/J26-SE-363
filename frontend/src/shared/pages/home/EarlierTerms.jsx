import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { Card } from '@/components/ui/card'
import { TeamRoleBadge } from '../../components/TeamBadges.jsx'

/** Teams from terms before the latest one, so past work is not lost from sight. */
export default function EarlierTerms({ teams }) {
  if (teams.length === 0) return null
  return (
    <Card className="gap-0 p-0">
      <h2 className="border-b border-border px-4 py-3 text-sm font-semibold text-foreground">Earlier terms</h2>
      <ul className="divide-y divide-border">
        {teams.map((team) => (
          <li key={team.id}>
            <Link
              to={`/teams/${team.code}`}
              className="flex items-center gap-3 px-4 py-2.5 text-sm outline-none hover:bg-muted/40 focus-visible:bg-muted/40"
            >
              <span className="w-20 shrink-0 text-muted-foreground">{team.term ?? '—'}</span>
              <span className="min-w-0 flex-1 truncate">
                <span className="font-medium text-foreground">{team.name}</span>
                {team.leader && team.my_role !== 'leader' && (
                  <span className="text-muted-foreground"> · led by {team.leader.name}</span>
                )}
              </span>
              <TeamRoleBadge role={team.my_role} />
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  )
}

EarlierTerms.propTypes = { teams: PropTypes.arrayOf(PropTypes.object).isRequired }

import PropTypes from 'prop-types'
import { Link, useNavigate } from 'react-router-dom'
import { Card } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { teamHref } from '../../utils/teams.js'
import { TeamRoleBadge, TeamStatusBadge } from '../../components/TeamBadges.jsx'


/** Lecturers: every team in a table, with who is still to answer. */
export function TeamsTable({ teams }) {
  const navigate = useNavigate()
  return (
    <Card className="gap-0 overflow-hidden p-0">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="pl-4">Team</TableHead>
            <TableHead>Project</TableHead>
            <TableHead className="w-24">Term</TableHead>
            <TableHead className="w-24">Students</TableHead>
            <TableHead>Leader</TableHead>
            <TableHead className="w-28">Status</TableHead>
            <TableHead className="w-24 pr-4 text-right">Waiting</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {teams.map((team) => (
            <TableRow
              key={team.id}
              className="cursor-pointer"
              onClick={() => navigate(teamHref(team))}
            >
              <TableCell className="pl-4">
                <Link
                  to={teamHref(team)}
                  onClick={(event) => event.stopPropagation()}
                  className="font-medium text-foreground hover:underline"
                >
                  {team.name}
                </Link>
                <p className="font-mono text-xs text-muted-foreground">{team.code}</p>
              </TableCell>
              <TableCell className="max-w-[240px] truncate text-muted-foreground">
                {team.project?.title ?? '—'}
              </TableCell>
              <TableCell className="text-muted-foreground">{team.term ?? '—'}</TableCell>
              <TableCell className="tabular-nums">{team.student_count}</TableCell>
              <TableCell className="text-muted-foreground">{team.leader?.name ?? '—'}</TableCell>
              <TableCell>
                <TeamStatusBadge status={team.status} />
              </TableCell>
              <TableCell className="pr-4 text-right tabular-nums text-muted-foreground">
                {team.pending_invitations ?? 0}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  )
}

TeamsTable.propTypes = { teams: PropTypes.arrayOf(PropTypes.object).isRequired }

/** Students: a card per team. */
export function TeamCards({ teams }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {teams.map((team) => (
        <Link
          key={team.id}
          to={teamHref(team)}
          className="rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Card className="card-hover-lift h-full gap-3 p-4">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="truncate text-sm font-semibold text-foreground">{team.name}</h3>
                <p className="font-mono text-xs text-muted-foreground">{team.code}</p>
              </div>
              <TeamRoleBadge role={team.my_role} />
            </div>
            <p className="line-clamp-2 min-h-10 text-sm text-muted-foreground">
              {team.project?.title ?? 'No project yet'}
            </p>
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{[team.term, `${team.student_count} students`].filter(Boolean).join(' · ')}</span>
              <TeamStatusBadge status={team.status} />
            </div>
          </Card>
        </Link>
      ))}
    </div>
  )
}

TeamCards.propTypes = { teams: PropTypes.arrayOf(PropTypes.object).isRequired }

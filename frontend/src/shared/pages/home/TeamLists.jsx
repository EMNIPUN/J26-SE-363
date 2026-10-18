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


/** Lecturers: every team in a table, with who has joined, who is still to answer and the repository. */
export function TeamsTable({ teams }) {
  const navigate = useNavigate()
  return (
    <Card className="gap-0 overflow-hidden p-0">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="pl-4">Team</TableHead>
            <TableHead className="w-24">Term</TableHead>
            <TableHead className="w-36">Students</TableHead>
            <TableHead>Leader</TableHead>
            <TableHead className="w-28">Repository</TableHead>
            <TableHead className="w-28 pr-4">Status</TableHead>
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
                <p className="max-w-[260px] truncate text-xs text-muted-foreground">
                  <span className="font-mono">{team.code}</span>
                  {team.project?.title ? ` · ${team.project.title}` : ''}
                </p>
              </TableCell>
              <TableCell className="text-muted-foreground">{team.term ?? '—'}</TableCell>
              <TableCell>
                <span className="tabular-nums">{team.student_count}</span>
                <span className="text-muted-foreground"> joined</span>
                {team.pending_student_invitations > 0 && (
                  <p className="text-xs tabular-nums text-amber-700 dark:text-amber-400">
                    {team.pending_student_invitations} waiting
                  </p>
                )}
              </TableCell>
              <TableCell className="text-muted-foreground">{team.leader?.name ?? '—'}</TableCell>
              <TableCell className="text-sm">
                {team.repo_url ? (
                  <a
                    href={team.repo_url}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(event) => event.stopPropagation()}
                    className="text-primary hover:underline"
                  >
                    Linked
                  </a>
                ) : (
                  <span className="text-muted-foreground">Not linked</span>
                )}
              </TableCell>
              <TableCell className="pr-4">
                <TeamStatusBadge status={team.status} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  )
}

TeamsTable.propTypes = { teams: PropTypes.arrayOf(PropTypes.object).isRequired }

/** Students: their teams in a table: the term, their role, who leads and the repository. */
export function StudentTeamsTable({ teams }) {
  const navigate = useNavigate()
  return (
    <Card className="gap-0 overflow-hidden p-0">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[34%] pl-4">Team</TableHead>
            <TableHead className="w-24">Term</TableHead>
            <TableHead className="w-28">Your role</TableHead>
            <TableHead>Leader</TableHead>
            <TableHead className="w-28">Repository</TableHead>
            <TableHead className="w-28 pr-4">Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {teams.map((team) => (
            <TableRow key={team.id} className="cursor-pointer" onClick={() => navigate(teamHref(team))}>
              <TableCell className="pl-4">
                <Link
                  to={teamHref(team)}
                  onClick={(event) => event.stopPropagation()}
                  className="font-medium text-foreground hover:underline"
                >
                  {team.name}
                </Link>
                <p className="max-w-[260px] truncate text-xs text-muted-foreground">
                  <span className="font-mono">{team.code}</span>
                  {team.project?.title ? ` · ${team.project.title}` : ''}
                </p>
              </TableCell>
              <TableCell className="text-muted-foreground">{team.term ?? '—'}</TableCell>
              <TableCell>
                <TeamRoleBadge role={team.my_role} />
              </TableCell>
              <TableCell className="text-muted-foreground">
                {team.my_role === 'leader' ? 'You' : (team.leader?.name ?? '—')}
              </TableCell>
              <TableCell className="text-sm">
                {team.repo_url ? (
                  <a
                    href={team.repo_url}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(event) => event.stopPropagation()}
                    className="text-primary hover:underline"
                  >
                    Linked
                  </a>
                ) : (
                  <span className="text-muted-foreground">Not linked</span>
                )}
              </TableCell>
              <TableCell className="pr-4">
                <TeamStatusBadge status={team.status} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  )
}

StudentTeamsTable.propTypes = { teams: PropTypes.arrayOf(PropTypes.object).isRequired }

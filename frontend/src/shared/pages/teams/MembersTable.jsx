import PropTypes from 'prop-types'
import { MoreHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import Avatar from '../../components/Avatar.jsx'
import { TeamRoleBadge } from '../../components/TeamBadges.jsx'
import { formatDate } from '../../utils/teams.js'

/**
 * Who can do what to a member:
 *   lecturers  remove anyone, and offer leadership to a student
 *   the leader offer leadership to another student
 *   everyone   leave
 */
function actionsFor({ member, myId, isLecturer, isLeader }) {
  const isMe = member.user_id === myId
  const isStudent = member.role !== 'lecturer'
  return {
    leave: isMe,
    remove: isLecturer && !isMe,
    offerLeadership: (isLecturer || isLeader) && isStudent && member.role !== 'leader',
  }
}

export default function MembersTable({
  members,
  myId,
  isLecturer,
  isLeader,
  onLeave,
  onRemove,
  onOfferLeadership,
  busyUserId,
}) {
  return (
    <Card className="gap-0 overflow-hidden p-0">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="pl-4">Name</TableHead>
            <TableHead className="w-28">Role</TableHead>
            <TableHead>GitHub</TableHead>
            {isLecturer && <TableHead>Email</TableHead>}
            <TableHead className="w-28">Joined</TableHead>
            <TableHead className="w-12 pr-4">
              <span className="sr-only">Actions</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {members.map((member) => {
            const actions = actionsFor({ member, myId, isLecturer, isLeader })
            const hasActions = actions.leave || actions.remove || actions.offerLeadership
            return (
              <TableRow key={member.user_id}>
                <TableCell className="pl-4">
                  <div className="flex items-center gap-2.5">
                    <Avatar name={member.name} picture={member.picture} size={28} />
                    <span className="font-medium text-foreground">
                      {member.name}
                      {member.user_id === myId && (
                        <span className="ml-1.5 text-xs font-normal text-muted-foreground">You</span>
                      )}
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <TeamRoleBadge role={member.role} />
                </TableCell>
                <TableCell className="text-muted-foreground">{member.github_username ?? '—'}</TableCell>
                {isLecturer && <TableCell className="text-muted-foreground">{member.email ?? '—'}</TableCell>}
                <TableCell className="text-muted-foreground">{formatDate(member.joined_at)}</TableCell>
                <TableCell className="pr-4 text-right">
                  {hasActions && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          loading={busyUserId === member.user_id}
                          aria-label={`Actions for ${member.name}`}
                        >
                          <MoreHorizontal aria-hidden="true" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {actions.offerLeadership && (
                          <DropdownMenuItem onClick={() => onOfferLeadership(member)}>
                            Offer leadership
                          </DropdownMenuItem>
                        )}
                        {actions.offerLeadership && (actions.leave || actions.remove) && (
                          <DropdownMenuSeparator />
                        )}
                        {actions.leave && (
                          <DropdownMenuItem
                            variant="destructive"
                            onClick={() => onLeave(member)}
                          >
                            Leave team
                          </DropdownMenuItem>
                        )}
                        {actions.remove && (
                          <DropdownMenuItem
                            variant="destructive"
                            onClick={() => onRemove(member)}
                          >
                            Remove from team
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </Card>
  )
}

MembersTable.propTypes = {
  members: PropTypes.arrayOf(PropTypes.object).isRequired,
  myId: PropTypes.string.isRequired,
  isLecturer: PropTypes.bool.isRequired,
  isLeader: PropTypes.bool.isRequired,
  onLeave: PropTypes.func.isRequired,
  onRemove: PropTypes.func.isRequired,
  onOfferLeadership: PropTypes.func.isRequired,
}

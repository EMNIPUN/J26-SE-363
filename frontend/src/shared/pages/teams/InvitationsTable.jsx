import PropTypes from 'prop-types'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { InvitationStateBadge } from '../../components/TeamBadges.jsx'
import { formatDate } from '../../utils/teams.js'

const roleLabel = (invitation) => {
  if (invitation.role === 'lecturer') return 'Lecturer'
  return invitation.as_leader ? 'Student, leader' : 'Student'
}

/** Invitations that have not been accepted, for the team's lecturers. */
export default function InvitationsTable({ invitations, busy, onResend, onWithdraw }) {
  return (
    <Card className="gap-0 overflow-hidden p-0">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="pl-4">Email</TableHead>
            <TableHead className="w-36">Invited as</TableHead>
            <TableHead className="w-28">Status</TableHead>
            <TableHead className="w-28">Expires</TableHead>
            <TableHead className="w-44 pr-4 text-right">
              <span className="sr-only">Actions</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {invitations.map((invitation) => {
            const open = invitation.status === 'pending' || invitation.status === 'expired'
            return (
              <TableRow key={invitation.id}>
                <TableCell className="pl-4 font-medium text-foreground">{invitation.email}</TableCell>
                <TableCell className="text-muted-foreground">{roleLabel(invitation)}</TableCell>
                <TableCell>
                  <InvitationStateBadge state={invitation.status} />
                </TableCell>
                <TableCell className="text-muted-foreground">{formatDate(invitation.expires_at)}</TableCell>
                <TableCell className="pr-4 text-right">
                  {open && (
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={busy}
                        onClick={() => onResend(invitation)}
                      >
                        Send again
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={busy}
                        onClick={() => onWithdraw(invitation)}
                      >
                        Withdraw
                      </Button>
                    </div>
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

InvitationsTable.propTypes = {
  invitations: PropTypes.arrayOf(PropTypes.object).isRequired,
  busy: PropTypes.bool,
  onResend: PropTypes.func.isRequired,
  onWithdraw: PropTypes.func.isRequired,
}

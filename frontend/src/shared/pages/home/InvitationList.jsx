import PropTypes from 'prop-types'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { describeInvitation } from '../../utils/teams.js'

/** Invitations waiting for an answer, with Accept and Decline. */
export default function InvitationList({ invitations, onAccept, onDecline, busyId }) {
  return (
    <Card className="gap-0 p-0">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">
          Invitations <span className="font-normal text-muted-foreground">({invitations.length})</span>
        </h2>
      </div>
      <ul className="divide-y divide-border">
        {invitations.map((invitation) => (
          <li
            key={invitation.id}
            className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">
                {invitation.team_name}{' '}
                <span className="font-mono text-xs font-normal text-muted-foreground">
                  {invitation.team_code}
                </span>
              </p>
              <p className="text-sm text-muted-foreground">
                {invitation.invited_by ? `${invitation.invited_by} invited you` : 'You are invited'}{' '}
                {describeInvitation(invitation)}
                {invitation.term ? ` · ${invitation.term}` : ''}
              </p>
            </div>
            <div className="flex shrink-0 gap-2">
              <Button
                variant="outline"
                disabled={busyId === invitation.id}
                onClick={() => onDecline(invitation.id)}
              >
                Decline
              </Button>
              <Button disabled={busyId === invitation.id} onClick={() => onAccept(invitation.id)}>
                Accept
              </Button>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  )
}

InvitationList.propTypes = {
  invitations: PropTypes.arrayOf(PropTypes.object).isRequired,
  onAccept: PropTypes.func.isRequired,
  onDecline: PropTypes.func.isRequired,
  busyId: PropTypes.string,
}

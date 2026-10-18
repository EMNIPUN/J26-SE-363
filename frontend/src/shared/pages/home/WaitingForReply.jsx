import PropTypes from 'prop-types'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useResendInvitation, useSentInvitations } from '../../hooks/useTeams.js'
import { ageLabel, daysSince } from '../../utils/teams.js'

const SHOWN = 5
const STALE_DAYS = 3

function Row({ invitation }) {
  const resend = useResendInvitation(invitation.team_code)
  const days = daysSince(invitation.created_at)
  return (
    <li className="flex items-center gap-3 px-4 py-2.5">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">{invitation.email}</p>
        <p className="truncate text-xs text-muted-foreground">
          {invitation.team_name} ·{' '}
          <span className={days >= STALE_DAYS ? 'text-amber-700 dark:text-amber-400' : undefined}>
            sent {ageLabel(days)}{days > 0 ? ' ago' : ''}
          </span>
        </p>
      </div>
      <Button
        size="sm"
        variant="ghost"
        loading={resend.isPending}
        onClick={() => resend.mutate(invitation.id)}
      >
        Send again
      </Button>
    </li>
  )
}

Row.propTypes = { invitation: PropTypes.object.isRequired }

/** Invitations a lecturer sent that nobody has answered, oldest first, with a way to nudge. */
export default function WaitingForReply() {
  const sent = useSentInvitations()
  const list = sent.data ?? []
  if (list.length === 0) return null

  return (
    <Card className="gap-0 p-0">
      <h2 className="border-b border-border px-4 py-3 text-sm font-semibold text-foreground">
        Waiting for a reply <span className="font-normal text-muted-foreground">({list.length})</span>
      </h2>
      <ul className="divide-y divide-border">
        {list.slice(0, SHOWN).map((invitation) => (
          <Row key={invitation.id} invitation={invitation} />
        ))}
      </ul>
      {list.length > SHOWN && (
        <p className="border-t border-border px-4 py-2 text-xs text-muted-foreground">
          Showing the {SHOWN} oldest of {list.length}.
        </p>
      )}
    </Card>
  )
}

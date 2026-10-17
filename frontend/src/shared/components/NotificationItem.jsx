import PropTypes from 'prop-types'
import { useNavigate } from 'react-router-dom'
import { Crown, Mail, UserCheck, UserMinus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  useAcceptInvitation,
  useDeclineInvitation,
  useRespondToLeadership,
} from '../hooks/useTeams.js'
import { useDismissNotification, useMarkRead } from '../hooks/useNotifications.js'
import { timeAgo } from '../utils/time.js'

const ICONS = {
  team_invitation: Mail,
  invitation_answered: UserCheck,
  leadership_offered: Crown,
  leadership_answered: Crown,
  leadership_withdrawn: Crown,
  member_left: UserMinus,
  member_removed: UserMinus,
}

// Accept and Decline right in the notification. Each answers through the same endpoint the team
// page uses, so there is one way to answer; the notification closes itself afterwards.
function LeadershipActions({ item }) {
  const respond = useRespondToLeadership(item.data.team_code)
  return (
    <>
      <Button size="sm" loading={respond.isPending && respond.variables === true} disabled={respond.isPending} onClick={() => respond.mutate(true)}>
        Accept
      </Button>
      <Button size="sm" variant="outline" loading={respond.isPending && respond.variables === false} disabled={respond.isPending} onClick={() => respond.mutate(false)}>
        Decline
      </Button>
    </>
  )
}

function InvitationActions({ item }) {
  const navigate = useNavigate()
  const accept = useAcceptInvitation()
  const decline = useDeclineInvitation()
  const busy = accept.isPending || decline.isPending
  const id = item.data.invitation_id
  return (
    <>
      <Button
        size="sm"
        loading={accept.isPending}
        disabled={busy}
        onClick={() => accept.mutate(id, { onSuccess: (team) => navigate(`/teams/${team.code}`) })}
      >
        Accept
      </Button>
      <Button size="sm" variant="outline" loading={decline.isPending} disabled={busy} onClick={() => decline.mutate(id)}>
        Decline
      </Button>
    </>
  )
}

/** One notification: what happened, when, and, while it is open, the buttons to answer it. */
export default function NotificationItem({ item, onNavigate, compact = false }) {
  const navigate = useNavigate()
  const markRead = useMarkRead()
  const dismiss = useDismissNotification()
  const Icon = ICONS[item.kind] ?? Mail

  const open = () => {
    if (!item.read) markRead.mutate(item.id)
    if (item.link) navigate(item.link)
    onNavigate?.()
  }

  return (
    <li className={cn('group relative flex gap-3 p-3.5', item.read ? 'bg-transparent' : 'bg-primary/5')}>
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border/60 bg-muted">
        <Icon className="h-4 w-4 text-primary" aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1 pr-5">
        <button
          type="button"
          onClick={open}
          className="block w-full cursor-pointer text-left outline-none focus-visible:underline"
        >
          <span className="flex items-center gap-1.5">
            <span className={cn('text-sm leading-snug', item.read ? 'text-foreground/90' : 'font-semibold text-foreground')}>
              {item.title}
            </span>
            {!item.read && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-label="Unread" />}
          </span>
          {item.body && !compact && <span className="mt-0.5 block text-xs text-muted-foreground">{item.body}</span>}
          <span className="mt-0.5 block text-xs text-muted-foreground/70">{timeAgo(item.created_at)}</span>
        </button>
        {item.actions.length > 0 && (
          <div className="mt-2 flex gap-2">
            {item.kind === 'leadership_offered' ? <LeadershipActions item={item} /> : <InvitationActions item={item} />}
          </div>
        )}
      </div>
      <button
        type="button"
        aria-label="Dismiss notification"
        onClick={() => dismiss.mutate(item.id)}
        className="absolute right-2 top-2 cursor-pointer rounded p-1 text-muted-foreground opacity-0 outline-none transition-opacity hover:text-foreground focus-visible:opacity-100 group-hover:opacity-100"
      >
        <X className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    </li>
  )
}

NotificationItem.propTypes = {
  item: PropTypes.shape({
    id: PropTypes.string.isRequired,
    kind: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    body: PropTypes.string,
    link: PropTypes.string,
    data: PropTypes.object.isRequired,
    read: PropTypes.bool.isRequired,
    created_at: PropTypes.string.isRequired,
    actions: PropTypes.arrayOf(PropTypes.string).isRequired,
  }).isRequired,
  onNavigate: PropTypes.func,
  compact: PropTypes.bool,
}

import { Link } from 'react-router-dom'
import { Bell, CheckCircle2, Mail } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useMyInvitations } from '../hooks/useTeams.js'
import { describeInvitation } from '../utils/teams.js'

/**
 * The bell in the top bar, styled like the one inside a team's workspace. Here it lists real
 * things waiting for the person: today, team invitations. More kinds can be added as items.
 */
export default function HubNotifications() {
  const invitations = useMyInvitations().data ?? []
  const count = invitations.length

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative h-9 w-9 cursor-pointer text-muted-foreground transition-transform hover:text-foreground active:scale-95"
          aria-label={`Notifications, ${count} new`}
        >
          <Bell className="h-4 w-4" />
          {count > 0 && (
            <span className="absolute right-1.5 top-1.5 flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={8}
        className="w-[360px] overflow-hidden rounded-xl border-border bg-popover p-0 shadow-2xl sm:w-[400px]"
      >
        <div className="flex items-center justify-between border-b border-border bg-muted/20 p-3.5">
          <span className="text-sm font-semibold tracking-tight text-foreground">Notifications</span>
          {count > 0 ? (
            <Badge variant="secondary" className="h-4 px-1.5 py-0 text-[10px] font-normal">
              {count} new
            </Badge>
          ) : (
            <Badge variant="outline" className="h-4 px-1.5 py-0 text-[10px] font-normal text-muted-foreground">
              Caught up
            </Badge>
          )}
        </div>

        <div className="max-h-[340px] divide-y divide-border/40 overflow-y-auto">
          {count === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-center">
              <CheckCircle2 className="mb-2 h-8 w-8 stroke-[1.5] text-muted-foreground/50" />
              <p className="text-xs font-medium text-foreground">No notifications</p>
              <p className="mt-0.5 text-[11px] text-muted-foreground">Your inbox is clear.</p>
            </div>
          ) : (
            invitations.map((invitation) => (
              <Link
                key={invitation.id}
                to="/invitations"
                className="flex items-start gap-3 bg-muted/15 p-3.5 outline-none transition-colors hover:bg-muted/50 focus-visible:bg-muted/50"
              >
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border/60 bg-muted shadow-xs">
                  <Mail className="h-4 w-4 text-primary" aria-hidden="true" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-semibold text-foreground">
                    Invitation to {invitation.team_name}
                  </span>
                  <span className="mt-0.5 block text-[11px] leading-relaxed text-muted-foreground">
                    {invitation.invited_by ? `${invitation.invited_by} invited you` : 'You are invited'}{' '}
                    {describeInvitation(invitation)}
                  </span>
                </span>
              </Link>
            ))
          )}
        </div>

        {count > 0 && (
          <div className="border-t border-border px-3.5 py-2.5">
            <Link to="/invitations" className="text-xs font-medium text-primary hover:underline">
              View invitations
            </Link>
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}

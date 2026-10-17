import { useNavigate } from 'react-router-dom'
import { Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  useAcceptInvitation,
  useDeclineInvitation,
  useMyInvitations,
} from '../../hooks/useTeams.js'
import EmptyState from '../../components/EmptyState.jsx'
import PageHeader from '../../components/PageHeader.jsx'
import InvitationList from '../home/InvitationList.jsx'

/** Every invitation waiting for an answer: the page behind the Invitations tab. */
export default function InvitationsPage() {
  const navigate = useNavigate()
  const invitations = useMyInvitations()
  const accept = useAcceptInvitation()
  const decline = useDeclineInvitation()
  const busy = accept.isPending
    ? { id: accept.variables, action: 'accept' }
    : decline.isPending
      ? { id: decline.variables, action: 'decline' }
      : null

  return (
    <div className="mx-auto grid w-full max-w-3xl gap-6">
      <PageHeader title="Invitations" description="Teams that have invited you." />

      {invitations.isPending && (
        <div className="grid gap-3" aria-busy="true">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      )}

      {invitations.isError && (
        <Card className="items-start gap-3 p-4">
          <p className="text-sm text-destructive">Your invitations could not be loaded.</p>
          <Button variant="outline" loading={invitations.isFetching} onClick={() => invitations.refetch()}>
            Try again
          </Button>
        </Card>
      )}

      {invitations.isSuccess && invitations.data.length === 0 && (
        <EmptyState
          icon={Mail}
          title="No invitations"
          description="When a lecturer invites you to a team, the invitation shows up here."
        />
      )}

      {invitations.isSuccess && invitations.data.length > 0 && (
        <InvitationList
          invitations={invitations.data}
          busy={busy}
          onAccept={(id) =>
            accept.mutate(id, { onSuccess: (team) => navigate(`/teams/${team.code}`) })
          }
          onDecline={decline.mutate}
        />
      )}
    </div>
  )
}

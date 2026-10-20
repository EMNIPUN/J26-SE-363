import { useState } from 'react'
import PropTypes from 'prop-types'
import { useNavigate, useParams } from 'react-router-dom'
import { UserPlus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '../../auth/useAuth.js'
import {
  useOfferLeadership,
  useRemoveMember,
  useResendInvitation,
  useRespondToLeadership,
  useTeam,
  useWithdrawInvitation,
  useWithdrawLeadershipOffer,
} from '../../hooks/useTeams.js'
import { useConfirm } from '../../utils/useConfirm.js'
import PageHeader from '../../components/PageHeader.jsx'
import { TeamStatusBadge } from '../../components/TeamBadges.jsx'
import InvitationsTable from './InvitationsTable.jsx'
import InviteDialog from './InviteDialog.jsx'
import LeadershipBanner from './LeadershipBanner.jsx'
import MembersTable from './MembersTable.jsx'
import GithubLinkCard from '../../github/GithubLinkCard.jsx'

function Section({ title, children }) {
  return (
    <section className="grid gap-3">
      <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      {children}
    </section>
  )
}

export default function TeamMembersPage() {
  const { teamId } = useParams()
  const navigate = useNavigate()
  const confirm = useConfirm()
  const { account } = useAuth()
  const team = useTeam(teamId)
  const [inviteOpen, setInviteOpen] = useState(false)

  const removeMember = useRemoveMember(teamId)
  const offerLeadership = useOfferLeadership(teamId)
  const respondToLeadership = useRespondToLeadership(teamId)
  const withdrawOffer = useWithdrawLeadershipOffer(teamId)
  const resendInvitation = useResendInvitation(teamId)
  const withdrawInvitation = useWithdrawInvitation(teamId)

  if (team.isPending) return <Skeleton className="h-64 w-full" aria-busy="true" />
  if (team.isError) {
    return <p className="text-sm text-destructive">{team.error.message}</p>
  }

  const data = team.data
  const isLecturer = data.my_role === 'lecturer'
  const isLeader = data.my_role === 'leader'
  const offeredToMe = data.pending_leader?.user_id === account.id
  const openInvitations = data.invitations.filter((i) => i.status !== 'accepted')

  const leave = async (member) => {
    const ok = await confirm({
      title: 'Leave this team?',
      description: 'You will lose access to the team. A lecturer can invite you again.',
      confirmText: 'Leave team',
      tone: 'destructive',
    })
    if (ok) removeMember.mutate(member.user_id, { onSuccess: () => navigate('/home') })
  }

  const remove = async (member) => {
    const ok = await confirm({
      title: `Remove ${member.name}?`,
      description: 'They will lose access to this team.',
      confirmText: 'Remove',
      tone: 'destructive',
    })
    if (ok) removeMember.mutate(member.user_id)
  }

  const offer = async (member) => {
    const ok = await confirm({
      title: `Offer leadership to ${member.name}?`,
      description: 'They become the team leader once they accept. Until then nothing changes.',
      confirmText: 'Send offer',
    })
    if (ok) offerLeadership.mutate(member.user_id)
  }

  const withdraw = async (invitation) => {
    const ok = await confirm({
      title: 'Withdraw this invitation?',
      description: `${invitation.email} will no longer be able to join with it.`,
      confirmText: 'Withdraw',
      tone: 'destructive',
    })
    if (ok) withdrawInvitation.mutate(invitation.id)
  }

  return (
    <div className="grid gap-6">
      <PageHeader
        title={data.name}
        description={[data.code, data.term, data.project?.title].filter(Boolean).join(' · ')}
        actions={
          <>
            <TeamStatusBadge status={data.status} />
            {isLecturer && (
              <Button onClick={() => setInviteOpen(true)}>
                <UserPlus className="h-4 w-4" aria-hidden="true" />
                Invite people
              </Button>
            )}
          </>
        }
      />

      <LeadershipBanner
        pending={data.pending_leader}
        leader={data.leader}
        isOfferedToMe={offeredToMe}
        canWithdraw={isLecturer || isLeader}
        busy={
          respondToLeadership.isPending
            ? respondToLeadership.variables
              ? 'accept'
              : 'decline'
            : withdrawOffer.isPending
              ? 'withdraw'
              : null
        }
        onRespond={respondToLeadership.mutate}
        onWithdraw={withdrawOffer.mutate}
      />

      <Section title="Members">
        <MembersTable
          members={data.members}
          myId={account.id}
          isLecturer={isLecturer}
          isLeader={isLeader}
          onLeave={leave}
          onRemove={remove}
          onOfferLeadership={offer}
          busyUserId={
            (removeMember.isPending && removeMember.variables) ||
            (offerLeadership.isPending && offerLeadership.variables) ||
            null
          }
        />
      </Section>

      {isLecturer && openInvitations.length > 0 && (
        <Section title="Invitations">
          <InvitationsTable
            invitations={openInvitations}
            busy={
              resendInvitation.isPending
                ? { id: resendInvitation.variables, action: 'resend' }
                : withdrawInvitation.isPending
                  ? { id: withdrawInvitation.variables, action: 'withdraw' }
                  : null
            }
            onResend={(invitation) => resendInvitation.mutate(invitation.id)}
            onWithdraw={withdraw}
          />
        </Section>
      )}

      <Section title="Repository">
        <GithubLinkCard
          key={data.repo_url ?? ''}
          team={teamId}
          repoUrl={data.repo_url}
          canEditRepo={isLecturer || isLeader}
        />
      </Section>

      {isLecturer && (
        <InviteDialog
          team={teamId}
          hasLeader={Boolean(data.leader)}
          open={inviteOpen}
          onOpenChange={setInviteOpen}
        />
      )}
    </div>
  )
}

Section.propTypes = {
  title: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
}

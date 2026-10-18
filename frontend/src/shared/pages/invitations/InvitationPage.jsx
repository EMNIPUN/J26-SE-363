import PropTypes from 'prop-types'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '../../auth/useAuth.js'
import {
  useAcceptInvitation,
  useDeclineInvitation,
  useInvitationLookup,
} from '../../hooks/useTeams.js'
import { describeInvitation } from '../../utils/teams.js'
import InvitationsPage from './InvitationsPage.jsx'
import { teamHref } from '../../utils/teams.js'

function Notice({ title, children, actions }) {
  return (
    <Card className="mx-auto w-full max-w-md gap-3 p-6">
      <h1 className="text-lg font-semibold text-foreground">{title}</h1>
      <p className="text-sm text-muted-foreground">{children}</p>
      <div className="flex flex-wrap gap-2 pt-2">{actions}</div>
    </Card>
  )
}

Notice.propTypes = {
  title: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
  actions: PropTypes.node,
}

function ProblemNotice({ error, onSignOut }) {
  const home = (
    <Button asChild variant="outline">
      <Link to="/home">Go to your teams</Link>
    </Button>
  )
  if (error.code === 'invitation_wrong_account') {
    return (
      <Notice
        title="This invitation is for a different account"
        actions={
          <>
            <Button onClick={onSignOut}>Sign in with another account</Button>
            {home}
          </>
        }
      >
        {error.message}
      </Notice>
    )
  }
  if (error.code === 'email_not_verified') {
    return (
      <Notice title="Verify your email first" actions={home}>
        Open the verification email we sent you, then come back to this link.
      </Notice>
    )
  }
  if (error.code === 'invitation_invalid') {
    return (
      <Notice title="This invitation is no longer valid" actions={home}>
        It may have expired or been withdrawn. Ask the lecturer to send it again.
      </Notice>
    )
  }
  return (
    <Notice title="We could not open this invitation" actions={home}>
      {error.message}
    </Notice>
  )
}

ProblemNotice.propTypes = {
  error: PropTypes.shape({ code: PropTypes.string, message: PropTypes.string }).isRequired,
  onSignOut: PropTypes.func.isRequired,
}

/**
 * The page behind the link in an invitation email (/invitations?token=...). Without a token it is
 * the list of all invitations waiting, which is what the Invitations tab opens.
 */
export default function InvitationPage() {
  const [params] = useSearchParams()
  const token = params.get('token')
  const navigate = useNavigate()
  const { logout } = useAuth()
  const lookup = useInvitationLookup(token)
  const accept = useAcceptInvitation()
  const decline = useDeclineInvitation()

  if (!token) return <InvitationsPage />

  if (lookup.isPending) {
    return <Skeleton className="mx-auto h-56 w-full max-w-md" aria-busy="true" />
  }
  if (lookup.isError) return <ProblemNotice error={lookup.error} onSignOut={logout} />

  const invitation = lookup.data
  const busy = accept.isPending || decline.isPending
  const rows = [
    ['Invited by', invitation.invited_by],
    ['Role', describeInvitation(invitation).replace(/^as an? /, '')],
    ['Project', invitation.project_title],
    ['Term', invitation.term],
  ].filter(([, value]) => value)

  return (
    <Card className="mx-auto w-full max-w-md gap-5 p-6">
      <div>
        <p className="text-sm text-muted-foreground">You are invited to join</p>
        <h1 className="mt-1 text-xl font-semibold tracking-tight text-foreground">
          {invitation.team_name}
        </h1>
        <p className="font-mono text-xs text-muted-foreground">{invitation.team_code}</p>
      </div>

      <dl className="divide-y divide-border rounded-lg border border-border text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4 px-3 py-2">
            <dt className="text-muted-foreground">{label}</dt>
            <dd className="text-right font-medium first-letter:uppercase text-foreground">{value}</dd>
          </div>
        ))}
      </dl>

      <div className="flex gap-2">
        <Button
          className="flex-1"
          loading={accept.isPending}
          disabled={busy}
          onClick={() =>
            accept.mutate(invitation.id, { onSuccess: (team) => navigate(teamHref(team)) })
          }
        >
          Accept
        </Button>
        <Button
          variant="outline"
          className="flex-1"
          loading={decline.isPending}
          disabled={busy}
          onClick={() => decline.mutate(invitation.id, { onSuccess: () => navigate('/home') })}
        >
          Decline
        </Button>
      </div>
    </Card>
  )
}

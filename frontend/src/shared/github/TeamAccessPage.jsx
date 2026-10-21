import { Navigate, useParams, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth/useAuth.js'
import TeamAccessGate from './TeamAccessGate.jsx'
import { markPassed, safeNext } from './accessPassed.js'

// Written while rendering on purpose: the team guard reads it as soon as the person is sent on, so it must already be there.
function Passed({ who, team, next }) {
  markPassed(who, team)
  return <Navigate to={next} replace />
}

/**
 * The dedicated address of the access check: /teams/:teamId/access. A student is always sent here first. GitHub sends the person back here after installing
 * the App or signing in (the callback addresses), and only when the check passes does the dashboard open, at the page they were going to (?next=).
 */
export default function TeamAccessPage() {
  const { teamId } = useParams()
  const { user } = useAuth()
  const [params] = useSearchParams()
  const who = user?.email || 'me'
  return (
    <TeamAccessGate teamId={teamId}>
      <Passed who={who} team={teamId} next={safeNext(params.get('next'), teamId)} />
    </TeamAccessGate>
  )
}

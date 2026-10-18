import PropTypes from 'prop-types'
import Badge from './Badge.jsx'

const TEAM_STATUS = {
  pending: { tone: 'warning', label: 'Pending' },
  forming: { tone: 'neutral', label: 'Forming' },
  active: { tone: 'success', label: 'Active' },
}

const TEAM_ROLE = {
  lecturer: { tone: 'primary', label: 'Lecturer' },
  leader: { tone: 'primary', label: 'Leader' },
  member: { tone: 'neutral', label: 'Member' },
}

const INVITATION_STATE = {
  pending: { tone: 'warning', label: 'Waiting' },
  accepted: { tone: 'success', label: 'Accepted' },
  declined: { tone: 'danger', label: 'Declined' },
  revoked: { tone: 'neutral', label: 'Withdrawn' },
  expired: { tone: 'neutral', label: 'Expired' },
}

function Pill({ map, value }) {
  const { tone, label } = map[value] ?? { tone: 'neutral', label: value }
  return <Badge tone={tone}>{label}</Badge>
}

Pill.propTypes = { map: PropTypes.object.isRequired, value: PropTypes.string.isRequired }

export const TeamStatusBadge = ({ status }) => <Pill map={TEAM_STATUS} value={status} />
export const TeamRoleBadge = ({ role }) => <Pill map={TEAM_ROLE} value={role} />
export const InvitationStateBadge = ({ state }) => <Pill map={INVITATION_STATE} value={state} />

TeamStatusBadge.propTypes = { status: PropTypes.string.isRequired }
TeamRoleBadge.propTypes = { role: PropTypes.string.isRequired }
InvitationStateBadge.propTypes = { state: PropTypes.string.isRequired }

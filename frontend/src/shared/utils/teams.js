// What an invitation offers, in a phrase that follows "invited you": "as a lecturer".
export function describeInvitation(invitation) {
  if (invitation.role === 'lecturer') return 'as a lecturer'
  return invitation.as_leader ? 'as team leader' : 'as a team member'
}

export function formatDate(value) {
  return value
    ? new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
    : '—'
}

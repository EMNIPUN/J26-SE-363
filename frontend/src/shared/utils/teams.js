// What an invitation offers, in a phrase that follows "invited you": "as a lecturer".
export function describeInvitation(invitation) {
  if (invitation.role === 'lecturer') return 'as a lecturer'
  return invitation.as_leader ? 'as team leader' : 'as a team member'
}

/**
 * What is unfinished in each team, as one entry per problem. Lecturers see every team's gaps;
 * a student only sees what they can fix, which is the repository when they lead the team.
 */
export function needsAttention(teams, isStaff) {
  const items = []
  const add = (team, kind, message) => items.push({ key: `${team.id}-${kind}`, team, message })
  for (const team of teams) {
    if (isStaff) {
      if (team.student_count > 0 && !team.leader) add(team, 'leader', 'has no leader yet')
      if (!team.repo_url) add(team, 'repo', 'has no repository linked')
      if (team.pending_invitations > 0) {
        const count = team.pending_invitations
        add(team, 'invites', `has ${count} invitation${count === 1 ? '' : 's'} waiting for a reply`)
      }
    } else if (team.my_role === 'leader' && !team.repo_url) {
      add(team, 'repo', 'needs a repository link')
    }
  }
  return items
}

export function formatDate(value) {
  return value
    ? new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
    : '—'
}

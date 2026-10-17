// What an invitation offers, in a phrase that follows "invited you": "as a lecturer".
export function describeInvitation(invitation) {
  if (invitation.role === 'lecturer') return 'as a lecturer'
  return invitation.as_leader ? 'as team leader' : 'as a team member'
}

// Where a team opens: its workspace, or the setup steps while it is still pending.
export const teamHref = (team) =>
  team.status === 'pending' ? `/teams/new/${team.code}` : `/teams/${team.code}`

/** The most recent term among the teams that are set up (terms like "2026-S2" sort as text). */
export function latestTerm(teams) {
  const terms = teams.filter((team) => team.status !== 'pending' && team.term).map((team) => team.term)
  return terms.length ? terms.sort().at(-1) : null
}

/** The latest term's teams (and any still being set up), and everything older. */
export function splitByTerm(teams) {
  const latest = latestTerm(teams)
  const current = teams.filter((team) => team.status === 'pending' || !latest || team.term === latest)
  return { latest, current, earlier: teams.filter((team) => !current.includes(team)) }
}

/**
 * What is unfinished in each team, as one entry per problem. Lecturers see every team's gaps;
 * a student only sees what they can fix: the repository when they lead the team, and a leadership
 * offer waiting for them. A team still being set up has its own card on the home page.
 */
export function needsAttention(teams, isStaff) {
  const items = []
  const add = (team, kind, message, to) => items.push({ key: `${team.id}-${kind}`, team, message, to })
  for (const team of teams) {
    if (team.status === 'pending') continue
    if (team.leadership_offer_to_me) add(team, 'offer', 'has offered you leadership', `/teams/${team.code}/members`)
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

/** Things worth filling in on a profile; `role` is the app's role name ("student", "instructor"). */
export function profileChecklist(account, role) {
  const profile = account.profile ?? {}
  const filled = (value) => Boolean(value && String(value).trim())
  return [
    { key: 'picture', label: 'Add a profile picture', done: filled(account.picture), to: '/profile' },
    { key: 'institution', label: 'Add your institution', done: filled(profile.institution), to: '/profile' },
    role === 'student'
      ? { key: 'number', label: 'Add your student number', done: filled(profile.student_number), to: '/profile' }
      : { key: 'department', label: 'Add your department', done: filled(profile.department), to: '/profile' },
    { key: 'email', label: 'Verify your email', done: Boolean(account.email_verified), to: '/profile/security' },
  ]
}

const DAY_MS = 24 * 60 * 60 * 1000

/** Whole days since a date. */
export function daysSince(value, now = Date.now()) {
  return Math.max(0, Math.floor((now - new Date(value).getTime()) / DAY_MS))
}

export function ageLabel(days) {
  if (days === 0) return 'today'
  return days === 1 ? '1 day' : `${days} days`
}

export function formatDate(value) {
  return value
    ? new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
    : '—'
}

/**
 * What the gate in front of a team says, for each answer the Core API can give.
 * The API decides (live, against GitHub); this only turns the decision into words and into the three steps shown on the page.
 */

export const STEPS = [
  { id: 'repo', label: 'Repository linked', who: 'by the team leader' },
  { id: 'account', label: 'Your GitHub account', who: 'verified by GitHub' },
  { id: 'access', label: 'Access to the repository', who: 'collaborator with write access' },
]

/** done | current | failed | waiting, for each of the three steps. */
export function stepStates(gate) {
  const s = gate?.state
  const order = ['repo_not_linked', 'account_not_linked', 'access']
  const at = s === 'repo_not_linked' ? 0 : s === 'account_not_linked' ? 1 : 2
  const out = order.map((_, i) => (i < at ? 'done' : i === at ? 'current' : 'waiting'))
  if (s === 'ok') return ['done', 'done', 'done']
  if (s === 'read_only' || s === 'no_access') out[2] = 'failed'
  return out
}

export function gateCopy(gate, team) {
  const name = team || gate?.team_name || 'this team'
  const me = gate?.login ? `@${gate.login}` : 'your GitHub account'
  const leader = gate?.leader_name || 'your team leader'
  switch (gate?.state) {
    case 'repo_not_linked':
      return gate.is_leader
        ? { tone: 'action', title: 'Link your team’s repository', body: 'Install the SELVIA GitHub App on the repository your team works in, then choose it. Your teammates can connect as soon as you have.', primary: 'repo' }
        : { tone: 'wait', title: 'Waiting for your team leader', body: `${leader} has not linked ${name}’s repository yet. You can enter as soon as they do. Nothing else is needed from you until then.`, primary: 'recheck' }
    case 'account_not_linked':
      return { tone: 'action', title: `Sign in with GitHub to enter ${name}`, body: 'GitHub tells us which account is yours, so your work is credited to you and to nobody else. You do this once; the check repeats every time you open the team.', primary: 'connect' }
    case 'read_only':
      return { tone: 'reject', title: 'Your account can only read this repository', body: `${me} is connected, but it has read access only. Ask ${leader} to add you as a collaborator with write access, then check again. If you used the wrong GitHub account, connect another one.`, primary: 'recheck', secondary: 'switch' }
    case 'no_access':
      return { tone: 'reject', title: `${me} is not a collaborator of this repository`, body: `GitHub says this account has no access. Ask ${leader} to add you as a collaborator, then check again. If you used the wrong GitHub account, sign in with the right one.`, primary: 'recheck', secondary: 'switch' }
    case 'github_unavailable':
      return { tone: 'wait', title: 'GitHub could not be reached', body: 'Your access could not be checked right now. Nothing is wrong with your account. Try again in a moment.', primary: 'recheck' }
    default:
      return { tone: 'wait', title: 'Checking your access', body: '', primary: null }
  }
}

/** The message behind ?github=error&reason=... after a sign-in came back with a problem. */
export function reasonText(reason) {
  return {
    github_account_taken: 'That GitHub account is already linked to another person, and one GitHub account can belong to only one team member. Sign in with your own account.',
    leader_must_link_first: 'The team leader has to link the repository first.',
  }[reason] || 'GitHub could not be linked. Try again.'
}

import apiClient from '@/shared/api/apiClient'

/**
 * GitHub linking, shared by every part of the platform (not only the assessment).
 * The team leader installs the GitHub App and picks the repository; each member then signs in to GitHub
 * from the team page so GitHub itself says which account is theirs. The API only stores GitHub's answers.
 */
export const githubService = {
  config: () => apiClient.get('/github/config'),
  team: (team) => apiClient.get(`/teams/${team}/github`),
  install: (team) => apiClient.post(`/teams/${team}/github/install`),
  repos: (team) => apiClient.get(`/teams/${team}/github/repos`),
  chooseRepo: (team, fullName) => apiClient.put(`/teams/${team}/github/repo`, { full_name: fullName }),
  unlink: (team) => apiClient.delete(`/teams/${team}/github`),
  refresh: (team) => apiClient.post(`/teams/${team}/github/refresh`),
  mine: () => apiClient.get('/me/github'),
  gate: (team) => apiClient.get(`/teams/${team}/gate`),
  connect: (team, back, chooseAccount = false) => apiClient.post('/me/github/connect', null, { params: { team, back, ...(chooseAccount ? { choose_account: true } : {}) } }),
  disconnect: () => apiClient.delete('/me/github'),
}

export const githubKeys = {
  config: ['github', 'config'],
  team: (team) => ['github', 'team', team],
  gate: (team) => ['github', 'gate', team],
  repos: (team) => ['github', 'repos', team],
  mine: ['github', 'mine'],
}

/** What each state of a member's link means, in words a student understands. */
export const MEMBER_STATE = {
  ready: { label: 'Ready', tone: 'success', help: 'Connected, and can write to the repository.' },
  read_only: { label: 'Read only', tone: 'warning', help: 'Connected, but the account can only read the repository. Ask the leader to add it as a collaborator with write access.' },
  no_access: { label: 'No access', tone: 'danger', help: 'Connected, but this GitHub account is not a collaborator of the repository.' },
  unchecked: { label: 'Not checked yet', tone: 'neutral', help: 'Connected. Access to the repository has not been checked yet.' },
  not_connected: { label: 'Not connected', tone: 'neutral', help: 'Has not connected a GitHub account yet.' },
}

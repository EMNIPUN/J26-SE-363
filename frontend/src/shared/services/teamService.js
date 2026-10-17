import apiClient from '@/shared/api/apiClient'
import { ENDPOINTS } from '@/shared/api/endpoints'

// `team` is a team's id or its code (e.g. "J26-SE-363").
export const teamService = {
  getMyTeams: () => apiClient.get(ENDPOINTS.TEAMS.MINE),
  getTeam: (team) => apiClient.get(ENDPOINTS.TEAMS.DETAIL(team)),
  createTeam: (payload) => apiClient.post(ENDPOINTS.TEAMS.CREATE, payload),
  updateTeam: (team, updates) => apiClient.patch(ENDPOINTS.TEAMS.DETAIL(team), updates),
  // Setting a team up: createTeam is step 1, then the project, the people, and activateTeam last.
  saveProject: (team, payload) => apiClient.put(ENDPOINTS.TEAMS.PROJECT(team), payload),
  activateTeam: (team) => apiClient.post(ENDPOINTS.TEAMS.ACTIVATE(team)),
  discardTeam: (team) => apiClient.delete(ENDPOINTS.TEAMS.DETAIL(team)),

  invite: (team, payload) => apiClient.post(ENDPOINTS.TEAMS.INVITATIONS(team), payload),
  resendInvitation: (team, invitationId) =>
    apiClient.post(ENDPOINTS.TEAMS.RESEND_INVITATION(team, invitationId)),
  withdrawInvitation: (team, invitationId) =>
    apiClient.delete(ENDPOINTS.TEAMS.INVITATION(team, invitationId)),

  removeMember: (team, userId) => apiClient.delete(ENDPOINTS.TEAMS.MEMBER(team, userId)),

  offerLeadership: (team, toUserId) =>
    apiClient.post(ENDPOINTS.TEAMS.LEADER_TRANSFER(team), { to_user_id: toUserId }),
  acceptLeadership: (team) => apiClient.post(ENDPOINTS.TEAMS.LEADER_ACCEPT(team)),
  declineLeadership: (team) => apiClient.post(ENDPOINTS.TEAMS.LEADER_DECLINE(team)),
  withdrawLeadershipOffer: (team) => apiClient.delete(ENDPOINTS.TEAMS.LEADER_TRANSFER(team)),

  getMyInvitations: () => apiClient.get(ENDPOINTS.INVITATIONS.MINE),
  lookupInvitation: (token) => apiClient.post(ENDPOINTS.INVITATIONS.LOOKUP, { token }),
  acceptInvitation: (invitationId) => apiClient.post(ENDPOINTS.INVITATIONS.ACCEPT(invitationId)),
  declineInvitation: (invitationId) => apiClient.post(ENDPOINTS.INVITATIONS.DECLINE(invitationId)),
}

export default teamService

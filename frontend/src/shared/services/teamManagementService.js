import apiClient from '@/shared/api/apiClient'
import { ENDPOINTS } from '@/shared/api/endpoints'

export const teamManagementService = {
  getTeams: (params) => apiClient.get(ENDPOINTS.TEAMS.LIST, { params }),
  getTeamDetail: (id) => apiClient.get(ENDPOINTS.TEAMS.DETAIL(id)),
  bulkCreateTeams: (payload) => apiClient.post(ENDPOINTS.TEAMS.BULK, payload),
  addMember: (teamId, payload) => apiClient.post(ENDPOINTS.TEAMS.ADD_MEMBER(teamId), payload),
  removeMember: (teamId, studentId) => apiClient.delete(ENDPOINTS.TEAMS.REMOVE_MEMBER(teamId, studentId)),
}

export default teamManagementService

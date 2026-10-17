import apiClient from '@/shared/api/apiClient'
import { ENDPOINTS } from '@/shared/api/endpoints'

export const cohortService = {
  // Batches
  getBatches: (params) => apiClient.get(ENDPOINTS.BATCHES.LIST, { params }),
  getBatchById: (id) => apiClient.get(ENDPOINTS.BATCHES.DETAIL(id)),
  createBatch: (payload) => apiClient.post(ENDPOINTS.BATCHES.CREATE, payload),
  updateBatch: (id, payload) => apiClient.patch(ENDPOINTS.BATCHES.UPDATE(id), payload),

  // Projects
  getProjects: (params) => apiClient.get(ENDPOINTS.PROJECTS.LIST, { params }),
  getProjectById: (id) => apiClient.get(ENDPOINTS.PROJECTS.DETAIL(id)),
  createProject: (payload) => apiClient.post(ENDPOINTS.PROJECTS.CREATE, payload),
}

export default cohortService

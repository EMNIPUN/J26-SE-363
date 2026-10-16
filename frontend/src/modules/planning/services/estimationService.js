import apiClient from '@/shared/api/apiClient.js'
import { ENDPOINTS } from '@/shared/api/endpoints.js'

export const estimationService = {
  saveEstimate: (body) => apiClient.post(ENDPOINTS.PLANNING.ESTIMATES, body),

  listEstimates: () => apiClient.get(ENDPOINTS.PLANNING.ESTIMATES),

  confirmEstimate: (storyRef) => apiClient.post(ENDPOINTS.PLANNING.ESTIMATE_CONFIRM(storyRef)),
}

export default estimationService

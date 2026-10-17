import apiClient from '@/shared/api/apiClient'
import { ENDPOINTS } from '@/shared/api/endpoints'

export const jobService = {
  publishJob: (payload) => apiClient.post(ENDPOINTS.JOBS.PUBLISH, payload),
  getJobStatus: (id) => apiClient.get(ENDPOINTS.JOBS.DETAIL(id)),
}

export default jobService

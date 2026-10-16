import apiClient from '@/shared/api/apiClient.js'
import { ENDPOINTS } from '@/shared/api/endpoints.js'

export const sessionService = {
  create: () => apiClient.post(ENDPOINTS.PLANNING.SESSIONS),

  getActive: () => apiClient.get(ENDPOINTS.PLANNING.SESSION_ACTIVE),

  getDetail: (id) => apiClient.get(ENDPOINTS.PLANNING.SESSION_DETAIL(id)),
}

export default sessionService

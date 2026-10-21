import apiClient from '@/shared/api/apiClient'
import { ENDPOINTS } from '@/shared/api/endpoints'

export const termService = {
  list: () => apiClient.get(ENDPOINTS.TERMS.LIST),
  create: (name) => apiClient.post(ENDPOINTS.TERMS.LIST, { name }),
}

export default termService

import apiClient from '@/shared/api/apiClient'
import { ENDPOINTS } from '@/shared/api/endpoints'

export const notificationService = {
  list: ({ limit, before } = {}) => apiClient.get(ENDPOINTS.NOTIFICATIONS.LIST, { params: { limit, before } }),
  markRead: (id) => apiClient.post(ENDPOINTS.NOTIFICATIONS.READ(id)),
  markAllRead: () => apiClient.post(ENDPOINTS.NOTIFICATIONS.READ_ALL),
  dismiss: (id) => apiClient.delete(ENDPOINTS.NOTIFICATIONS.ONE(id)),
  getPreferences: () => apiClient.get(ENDPOINTS.NOTIFICATIONS.PREFERENCES),
  setPreferences: (email) => apiClient.put(ENDPOINTS.NOTIFICATIONS.PREFERENCES, { email }),
}

export default notificationService

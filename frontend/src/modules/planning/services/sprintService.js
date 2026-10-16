import apiClient from '@/shared/api/apiClient.js'
import { ENDPOINTS } from '@/shared/api/endpoints.js'

export const sprintService = {
  listItems: () => apiClient.get(ENDPOINTS.PLANNING.BACKLOG),

  createItem: (body) => apiClient.post(ENDPOINTS.PLANNING.BACKLOG, body),

  updateItem: (id, patch) => apiClient.patch(ENDPOINTS.PLANNING.BACKLOG_ITEM(id), patch),

  deleteItem: (id) => apiClient.delete(ENDPOINTS.PLANNING.BACKLOG_ITEM(id)),

  // Backward compat aliases
  listTasks: () => apiClient.get(ENDPOINTS.PLANNING.BACKLOG),
  createTask: (body) => apiClient.post(ENDPOINTS.PLANNING.BACKLOG, body),
  updateTask: (id, patch) => apiClient.patch(ENDPOINTS.PLANNING.BACKLOG_ITEM(id), patch),
  deleteTask: (id) => apiClient.delete(ENDPOINTS.PLANNING.BACKLOG_ITEM(id)),
}

export default sprintService

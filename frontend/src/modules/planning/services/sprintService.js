import apiClient from '@/shared/api/apiClient.js'
import { ENDPOINTS } from '@/shared/api/endpoints.js'

export const sprintService = {
  listTasks: () => apiClient.get(ENDPOINTS.PLANNING.SPRINT_TASKS),

  createTask: (body) => apiClient.post(ENDPOINTS.PLANNING.SPRINT_TASKS, body),

  updateTask: (ref, patch) => apiClient.patch(ENDPOINTS.PLANNING.SPRINT_TASK(ref), patch),

  deleteTask: (ref) => apiClient.delete(ENDPOINTS.PLANNING.SPRINT_TASK(ref)),
}

export default sprintService

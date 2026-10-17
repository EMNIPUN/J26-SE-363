import apiClient from '@/shared/api/apiClient.js'
import { ENDPOINTS } from '@/shared/api/endpoints.js'

export const decompositionService = {
  listStories: () => apiClient.get(ENDPOINTS.PLANNING.STORIES),

  createStory: (story) => apiClient.post(ENDPOINTS.PLANNING.STORIES, story),

  updateStory: (ref, patch) => apiClient.patch(ENDPOINTS.PLANNING.STORY(ref), patch),

  createTask: (ref, task) => apiClient.post(ENDPOINTS.PLANNING.STORY_TASKS(ref), task),

  updateTask: (ref, taskId, patch) => apiClient.patch(ENDPOINTS.PLANNING.STORY_TASK(ref, taskId), patch),

  deleteTask: (ref, taskId) => apiClient.delete(ENDPOINTS.PLANNING.STORY_TASK(ref, taskId)),

  validateTasks: (ref, { tasks }) =>
    apiClient.post(ENDPOINTS.PLANNING.STORY_TASKS_VALIDATE(ref), { tasks }, { timeout: 120000 }),

  getTaskValidation: (ref) => apiClient.get(ENDPOINTS.PLANNING.STORY_TASKS_VALIDATION(ref)),

  deleteStory: (ref) => apiClient.delete(ENDPOINTS.PLANNING.STORY(ref)),

  analyzeDecomposition: ({ requirement, stories, threshold = 75 }) =>
    apiClient.post(ENDPOINTS.PLANNING.DECOMPOSITION, { requirement, stories, threshold }, { timeout: 180000 }),

  getResults: () => apiClient.get(ENDPOINTS.PLANNING.DECOMPOSITION),

  getHistory: (requirementRef) => apiClient.get(ENDPOINTS.PLANNING.DECOMPOSITION_HISTORY(requirementRef)),
}

export default decompositionService

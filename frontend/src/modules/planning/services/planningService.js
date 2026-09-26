import apiClient from '@/shared/api/apiClient.js'
import { ENDPOINTS } from '@/shared/api/endpoints.js'

/**
 * Planning Module API Service
 *
 * Encapsulates all network communication for project planning,
 * tasks, sprints, and timeline milestones.
 */
export const planningService = {
  /**
   * Get list of projects with optional filters
   * @param {Object} [params] - { status, page, limit }
   */
  getProjects: (params) => {
    return apiClient.get(ENDPOINTS.PLANNING.PROJECTS, { params })
  },

  /**
   * Get project details by ID
   * @param {string|number} projectId
   */
  getProjectById: (projectId) => {
    return apiClient.get(ENDPOINTS.PLANNING.PROJECT_DETAIL(projectId))
  },

  /**
   * Get tasks with optional project / assignee filtering
   * @param {Object} [params] - { projectId, status, assigneeId }
   */
  getTasks: (params) => {
    return apiClient.get(ENDPOINTS.PLANNING.TASKS, { params })
  },

  /**
   * Create a new project task
   * @param {Object} taskData - { title, description, projectId, priority, dueDate }
   */
  createTask: (taskData) => {
    return apiClient.post(ENDPOINTS.PLANNING.TASKS, taskData)
  },

  /**
   * Update an existing task
   * @param {string|number} taskId
   * @param {Object} updates
   */
  updateTask: (taskId, updates) => {
    return apiClient.patch(ENDPOINTS.PLANNING.TASK_DETAIL(taskId), updates)
  },

  /**
   * Delete a task
   * @param {string|number} taskId
   */
  deleteTask: (taskId) => {
    return apiClient.delete(ENDPOINTS.PLANNING.TASK_DETAIL(taskId))
  },

  /**
   * Get project timeline milestones
   * @param {string|number} projectId
   */
  getTimeline: (projectId) => {
    return apiClient.get(ENDPOINTS.PLANNING.TIMELINE(projectId))
  },
}

export default planningService

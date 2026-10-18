import apiClient from '@/shared/api/apiClient.js'
import { ENDPOINTS } from '@/shared/api/endpoints.js'

export const jiraService = {
  /**
   * Check connection and configuration status with Jira.
   * @param {Object} [params] - Optional query overrides (base_url, email, project_key)
   */
  getStatus: (params) => apiClient.get(ENDPOINTS.PLANNING.JIRA_STATUS, { params }),

  /**
   * Push current session backlog (Epics, Stories, Story Points, Sub-tasks) to Jira.
   * @param {Object} [body] - Optional credentials override, story_refs, story_points, force_resync
   */
  syncBacklog: (body = {}) =>
    apiClient.post(ENDPOINTS.PLANNING.JIRA_SYNC_BACKLOG, body, { timeout: 60000 }),

  /**
   * Create the active Sprint on Jira Scrum board and assign estimated stories to it.
   * @param {Object} [body] - { sprint_id, ...optional overrides }
   */
  syncSprint: (body = {}) =>
    apiClient.post(ENDPOINTS.PLANNING.JIRA_SYNC_SPRINT, body, { timeout: 60000 }),

  /**
   * Reset local database Jira keys to allow starting over / re-pushing fresh.
   */
  resetLinks: (body = {}) =>
    apiClient.post(ENDPOINTS.PLANNING.JIRA_RESET_LINKS, body, { timeout: 30000 }),
}

export default jiraService

import apiClient from '@/shared/api/apiClient.js'
import { ENDPOINTS } from '@/shared/api/endpoints.js'

/**
 * AI Tutor & Multi-Agent Orchestration Service
 *
 * Encapsulates network operations for conversational AI mentorship,
 * session transcripts, and automated multi-agent code/task reviews.
 */
export const tutorService = {
  /**
   * List available tutoring sessions
   */
  getSessions: () => {
    return apiClient.get(ENDPOINTS.TUTOR.SESSIONS)
  },

  /**
   * Send message to the AI Mentor Agent
   * @param {string|number} sessionId
   * @param {{ message: string, context?: Object }} payload
   */
  sendMessage: (sessionId, payload) => {
    return apiClient.post(ENDPOINTS.TUTOR.CHAT(sessionId), payload)
  },

  /**
   * Retrieve transcript history for a session
   * @param {string|number} sessionId
   */
  getSessionHistory: (sessionId) => {
    return apiClient.get(ENDPOINTS.TUTOR.CHAT(sessionId))
  },

  /**
   * Request multi-agent automated task & code review
   * @param {{ projectId: string|number, codeSnippet?: string, criteria?: string[] }} payload
   */
  requestReview: (payload) => {
    return apiClient.post(ENDPOINTS.TUTOR.REVIEWS, payload)
  },
}

export default tutorService

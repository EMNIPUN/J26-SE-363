import apiClient from '@/shared/api/apiClient.js'
import { ENDPOINTS } from '@/shared/api/endpoints.js'

/** Competency analysis can include Neo4j + OpenAI + MCP; allow a longer wait. */
const COMPETENCY_TIMEOUT_MS = 120000
const CHAT_TIMEOUT_MS = 60000

/**
 * Live Adaptive Tutor API (Core → AI Backend).
 * Identity comes from the Keycloak bearer token; never send studentId in the body.
 */
export const tutorApi = {
  /**
   * Run required-knowledge + BKT competency analysis.
   * @param {{ project_id?: string, sprint_id?: string, concept_ids?: string[] }} [payload]
   */
  estimateCompetency: (payload = {}) => {
    return apiClient.post(ENDPOINTS.TUTOR.COMPETENCY, payload, {
      timeout: COMPETENCY_TIMEOUT_MS,
    })
  },

  /**
   * Send a tutor chat message (MCP evidence path; no adaptive decision yet).
   * @param {{ message: string, request_id?: string }} payload
   */
  chat: (payload) => {
    return apiClient.post(ENDPOINTS.TUTOR.CHAT, payload, {
      timeout: CHAT_TIMEOUT_MS,
    })
  },
}

export default tutorApi

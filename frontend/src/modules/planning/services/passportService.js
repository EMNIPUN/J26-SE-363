import apiClient from '@/shared/api/apiClient.js'
import { ENDPOINTS } from '@/shared/api/endpoints.js'

export const passportService = {
  /**
   * List all backlog readiness passports for the active session
   */
  listPassports: () => apiClient.get(ENDPOINTS.PLANNING.PASSPORTS),

  /**
   * Get backlog readiness passport for a specific story reference
   */
  getPassport: (storyRef) => apiClient.get(ENDPOINTS.PLANNING.PASSPORT(storyRef)),

  /**
   * Trigger a recalculation/evaluation of readiness passport for a story
   */
  evaluatePassport: (storyRef) =>
    apiClient.post(ENDPOINTS.PLANNING.PASSPORTS_EVALUATE, { story_ref: storyRef }),
}

export default passportService

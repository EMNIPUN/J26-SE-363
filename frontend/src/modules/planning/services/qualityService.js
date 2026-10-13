import apiClient from '@/shared/api/apiClient.js'
import { ENDPOINTS } from '@/shared/api/endpoints.js'

/**
 * Requirement Quality Agent API service.
 *
 * Talks to the Core API (which forwards to the AI Backend's planning agent).
 * The apiClient response interceptor already unwraps `response.data`, so these
 * resolve to the agent's structured result directly.
 */
export const qualityService = {
  /**
   * Upload an SRS .docx -> backend extracts requirements and scores each one.
   * @param {File} file - the .docx file
   * @param {number} [threshold=75]
   * @returns {Promise<{count:number, requirements:Array, quality:Object}>}
   */
  uploadSrs: (file, threshold = 75) => {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post(ENDPOINTS.PLANNING.SRS, form, {
      params: { threshold },
      // Let the browser set multipart/form-data WITH its boundary (overrides the
      // client's default application/json). Setting it manually drops the boundary.
      headers: { 'Content-Type': undefined },
      timeout: 120000, // scoring several requirements can take longer than the 15s default
    })
  },

  /**
   * Score one or more typed-in requirements.
   * @param {Array<{id:string, text:string, type?:string}>} requirements
   * @param {number} [threshold=75]
   * @returns {Promise<{threshold:number, requirements:Array}>}
   */
  analyzeQuality: (requirements, threshold = 75) =>
    apiClient.post(ENDPOINTS.PLANNING.QUALITY, { requirements, threshold }, { timeout: 120000 }),
}

export default qualityService

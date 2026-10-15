import apiClient from '@/shared/api/apiClient.js'
import { ENDPOINTS } from '@/shared/api/endpoints.js'

export const dartService = {
  arbitrate: (payload) =>
    apiClient.post(ENDPOINTS.PLANNING.DART_ARBITRATE, payload, { timeout: 90000 }),

  getCases: (params = {}) =>
    apiClient.get(ENDPOINTS.PLANNING.DART_CASES, { params }),

  getCase: (caseRef) =>
    apiClient.get(ENDPOINTS.PLANNING.DART_CASE(caseRef)),

  resolveCase: (caseRef, body) =>
    apiClient.patch(ENDPOINTS.PLANNING.DART_RESOLVE(caseRef), body),
}

export default dartService

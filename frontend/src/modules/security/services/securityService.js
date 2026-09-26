// Domain service for the AEGIS Security module.
//
// The security subsystem's scanner/LLM pipeline is not implemented on the
// backend yet, so these functions resolve local mock data instead of
// calling apiClient. The function signatures and return shapes match what
// the eventual endpoints (see docs/API_GUIDELINES.md) will return, so
// swapping in real apiClient.get(...) calls later will not require any
// change in the hooks or pages that consume this service.
import { INITIAL_FINDINGS } from '../data/mockFindings.js'

const MOCK_LATENCY_MS = 250

function delay(value) {
  return new Promise((resolve) => setTimeout(() => resolve(value), MOCK_LATENCY_MS))
}

export const securityService = {
  // GET equivalent: /security/findings?teamId=
  getFindings: () => {
    return delay(INITIAL_FINDINGS)
  },

  // GET equivalent: /security/findings/:id
  getFindingById: (findingId) => {
    const finding = INITIAL_FINDINGS.find((item) => item.id === findingId) || null
    return delay(finding)
  },
}

export default securityService

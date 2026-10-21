// Read-only calls for the Security Assistant pages (Core API, /security-assistant/...).
// In demo mode (config.js) the same functions answer from the checked-in sample bundle instead, and nothing leaves the browser.
import apiClient from '@/shared/api/apiClient.js'
import { ENDPOINTS } from '@/shared/api/endpoints.js'
import { isDemoMode } from '../config.js'
import demoBundle from '../demo/demoBundle.json'

const E = ENDPOINTS.SECURITY_ASSISTANT

function demo(value) {
  return Promise.resolve(structuredClone(value))
}

function missing(what) {
  return Promise.reject(Object.assign(new Error(`${what} is not in the demo data`), { status: 404 }))
}

export const securityAssistantService = {
  runs: (team) => (isDemoMode() ? demo(demoBundle.runs) : apiClient.get(E.RUNS(team))),

  students: (team) => (isDemoMode() ? demo(demoBundle.students) : apiClient.get(E.STUDENTS(team))),

  run: (team, run, { student } = {}) =>
    isDemoMode()
      ? demoBundle.overview[run] ? demo(demoBundle.overview[run]) : missing('This run')
      : apiClient.get(E.RUN(team, run), { params: student ? { student } : undefined }),

  // Every finding of a run (summaries, newest risk first); the pages filter by type, status and "mine" themselves.
  findings: (team, run, { student } = {}) =>
    isDemoMode()
      ? demoBundle.findings[run] ? demo(demoBundle.findings[run]) : missing('This run')
      : apiClient.get(E.FINDINGS(team, run), { params: student ? { student } : undefined }),

  finding: (team, run, groupId, { student } = {}) =>
    isDemoMode()
      ? demoBundle.finding[run]?.[groupId] ? demo(demoBundle.finding[run][groupId]) : missing('This finding')
      : apiClient.get(E.FINDING(team, run, groupId), { params: student ? { student } : undefined }),

  // The probe questions and the (mock) Tutor's results of a run; the page filters "mine" itself.
  learning: (team, run, { student } = {}) =>
    isDemoMode()
      ? demoBundle.learning[run] ? demo(demoBundle.learning[run]) : missing('This run')
      : apiClient.get(E.LEARNING(team, run), { params: student ? { student } : undefined }),

  // The decision trails and the governance summary of a run.
  agents: (team, run) =>
    isDemoMode()
      ? demoBundle.agents[run] ? demo(demoBundle.agents[run]) : missing('This run')
      : apiClient.get(E.AGENTS(team, run)),

  // The workflow and agent graphs (nodes, edges, Mermaid text) and which nodes ran.
  workflow: (team, run) =>
    isDemoMode()
      ? demoBundle.workflow[run] ? demo(demoBundle.workflow[run]) : missing('This run')
      : apiClient.get(E.WORKFLOW(team, run)),

  // The audit log (hashes and counts only): lecturers and administrators. The page does not call this for a student.
  audit: (team, run, { limit = 500 } = {}) =>
    isDemoMode()
      ? demoBundle.audit[run] ? demo(demoBundle.audit[run]) : missing('This audit log')
      : apiClient.get(E.AUDIT(team, run), { params: { limit } }),
}

export default securityAssistantService

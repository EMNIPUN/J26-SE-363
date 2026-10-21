import apiClient from '@/shared/api/apiClient.js'
import tokenManager from '@/shared/api/tokenManager.js'

const P = '/performance'

/** Calls to the assessment routes of the Core API (apiClient already returns the response body). */
export const assessmentApi = {
  meta: () => apiClient.get(`${P}/meta`),
  overview: (team, sprint) => apiClient.get(`${P}/teams/${team}/overview`, { params: sprint ? { sprint } : {} }),
  development: (team, sprint) => apiClient.get(`${P}/teams/${team}/development`, { params: sprint ? { sprint } : {} }),
  setup: (team) => apiClient.get(`${P}/teams/${team}/setup`),
  saveSettings: (team, body) => apiClient.put(`${P}/teams/${team}/settings`, body),
  runs: (team, sprint) => apiClient.get(`${P}/teams/${team}/runs`, { params: sprint ? { sprint } : {} }),
  startRun: (team, sprint_id, mode, students) =>
    apiClient.post(`${P}/teams/${team}/runs`, {
      sprint_id,
      mode,
      ...(students && students.length ? { students } : {}),
    }),
  rerun: (runId) => apiClient.post(`${P}/runs/${runId}/rerun`),
  run: (id) => apiClient.get(`${P}/runs/${id}`),
  cancelRun: (id) => apiClient.post(`${P}/runs/${id}/cancel`),
  graph: () => apiClient.get(`${P}/graph`),
  events: (id, after = 0) => apiClient.get(`${P}/runs/${id}/events`, { params: { after, limit: 5000 } }),
  runReport: (id) => apiClient.get(`${P}/runs/${id}/report`, { responseType: 'text' }),
  identityMap: (id, body) => apiClient.post(`${P}/runs/${id}/identity-map`, body),
  trajectory: (team, sprint, student) => apiClient.get(`${P}/teams/${team}/sprints/${sprint}/students/${student}/trajectory`),
  report: (team, sprint, student) => apiClient.get(`${P}/teams/${team}/students/${student}/report`, { params: { sprint } }),
  trajectoryAll: (team, student) => apiClient.get(`${P}/teams/${team}/students/${student}/trajectory`),
  history: (team, student) => apiClient.get(`${P}/teams/${team}/students/${student}/history`),
  questions: (team, sprint, student, include = 'list') => apiClient.get(`${P}/teams/${team}/sprints/${sprint}/students/${student}/questions`, { params: { include } }),
  setMark: (team, sprint, student, body) => apiClient.put(`${P}/teams/${team}/sprints/${sprint}/students/${student}/override`, body),
  method: (team) => apiClient.get(`${P}/teams/${team}/method`),
  reviews: (status = 'open') => apiClient.get(`${P}/reviews`, { params: { status } }),
  decide: (id, body) => apiClient.post(`${P}/reviews/${id}/decision`, body),
  answer: (id, answers) => apiClient.post(`${P}/reviews/${id}/answer`, { answers }),
  myReports: (team) => apiClient.get(`${P}/me/reports`, { params: team ? { team } : {} }),
  myQuizzes: (team, status) => apiClient.get(`${P}/me/quizzes`, { params: { ...(team ? { team } : {}), ...(status ? { status } : {}) } }),
  answerQuiz: (id, answer) => apiClient.post(`${P}/me/quizzes/${id}/answer`, { answer }),
  clearEvaluation: (team, sprint) => apiClient.delete(`${P}/teams/${team}/evaluation`, { params: sprint ? { sprint } : {} }),
}


export const assessmentKeys = {
  meta: ['assessment', 'meta'],
  overview: (team, sprint) => ['assessment', team, 'overview', sprint || 'latest'],
  development: (team, sprint) => ['assessment', team, 'development', sprint || 'latest'],
  setup: (team) => ['assessment', team, 'setup'],
  runs: (team, sprint) => ['assessment', team, 'runs', sprint || 'all'],
  report: (team, sprint, student) => ['assessment', team, 'report', sprint, student],
  history: (team, student) => ['assessment', team, 'history', student],
  trajectory: (team, sprint, student) => ['assessment', team, 'trajectory', sprint, student],
  trajectoryAll: (team, student) => ['assessment', team, 'trajectory', 'all', student],
  questions: (team, sprint, student) => ['assessment', team, 'questions', sprint, student],
  reviews: ['assessment', 'reviews'],
  run: (id) => ['assessment', 'run', id],
  graph: ['assessment', 'graph'],
}

/** Where the event stream of a run is (EventSource cannot send the bearer token, so the stream is read with fetch). */
export function streamUrl(runId, after) {
  return `${apiClient.defaults.baseURL}${P}/runs/${runId}/stream?after=${after}`
}

export const bearer = () => {
  const t = tokenManager.getToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

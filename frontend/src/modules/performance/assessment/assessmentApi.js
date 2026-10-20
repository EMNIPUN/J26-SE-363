import apiClient from '@/shared/api/apiClient.js'
import tokenManager from '@/shared/api/tokenManager.js'

const P = '/performance'

/** Calls to the assessment routes of the Core API (apiClient already returns the response body). */
export const assessmentApi = {
  tracking: (team) => apiClient.get(`${P}/teams/${team}/tracking`),
  readiness: (team) => apiClient.get(`${P}/teams/${team}/readiness`),
  saveSettings: (team, body) => apiClient.put(`${P}/teams/${team}/settings`, body),
  runs: (team, sprint) => apiClient.get(`${P}/teams/${team}/runs`, { params: sprint ? { sprint } : {} }),
  startRun: (team, sprint_id, mode) => apiClient.post(`${P}/teams/${team}/runs`, { sprint_id, mode }),
  rerun: (runId) => apiClient.post(`${P}/runs/${runId}/rerun`),
  run: (id) => apiClient.get(`${P}/runs/${id}`),
  cancelRun: (id) => apiClient.post(`${P}/runs/${id}/cancel`),
  graph: () => apiClient.get(`${P}/graph`),
  events: (id, after = 0) => apiClient.get(`${P}/runs/${id}/events`, { params: { after, limit: 5000 } }),
  report: (id) => apiClient.get(`${P}/runs/${id}/report`, { responseType: 'text' }),
  identityMap: (id, body) => apiClient.post(`${P}/runs/${id}/identity-map`, body),
  results: (team, sprint) => apiClient.get(`${P}/teams/${team}/sprints/${sprint}/results`),
  trajectory: (team, sprint, student) => apiClient.get(`${P}/teams/${team}/sprints/${sprint}/students/${student}/trajectory`),
  quiz: (team, sprint, student) => apiClient.get(`${P}/teams/${team}/sprints/${sprint}/students/${student}/quiz`),
  setMark: (team, sprint, student, body) => apiClient.put(`${P}/teams/${team}/sprints/${sprint}/students/${student}/override`, body),
  reviews: (status = 'open') => apiClient.get(`${P}/reviews`, { params: { status } }),
  decide: (id, body) => apiClient.post(`${P}/reviews/${id}/decision`, body),
  myResults: () => apiClient.get(`${P}/me/results`),
  myQuizzes: () => apiClient.get(`${P}/me/quizzes`),
  answerQuiz: (id, answer) => apiClient.post(`${P}/me/quizzes/${id}/answer`, { answer }),
}

export const assessmentKeys = {
  tracking: (team) => ['assessment', team, 'tracking'],
  readiness: (team) => ['assessment', team, 'readiness'],
  runs: (team, sprint) => ['assessment', team, 'runs', sprint || 'all'],
  results: (team, sprint) => ['assessment', team, 'results', sprint],
  trajectory: (team, sprint, student) => ['assessment', team, 'trajectory', sprint, student],
  quiz: (team, sprint, student) => ['assessment', team, 'quiz', sprint, student],
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

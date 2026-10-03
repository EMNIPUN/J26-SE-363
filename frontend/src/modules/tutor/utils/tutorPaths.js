import { useParams } from 'react-router-dom'

export function getTutorPaths(teamId) {
  const base = `/teams/${teamId}/tutor`
  return {
    chat: `${base}/chat`,
    sprintGuidance: `${base}/learning`,
    exercises: `${base}/exercise`,
    assessments: `${base}/quiz`,
    progress: `${base}/results`,
    activity: (activityId) => `${base}/activity/${activityId}`,
    results: (assessmentId) => `${base}/results/${assessmentId}`,
  }
}

export function useTutorPaths() {
  const { teamId } = useParams()
  return getTutorPaths(teamId)
}

// Maps a backend recommendation/message action ({ kind, targetId }) to a route.
export function getActionPath(paths, action) {
  if (!action) return null
  switch (action.kind) {
    case 'activity':
      return paths.activity(action.targetId)
    default:
      return null
  }
}

import tutorApi from '../services/tutorApi.js'
import { useTutorQuery } from './useTutorQuery.js'

export function useSprintGuidance() {
  return useTutorQuery(['sprint-guidance'], tutorApi.getSprintGuidance)
}

export function useLearningLoop() {
  return useTutorQuery(['learning-loop'], tutorApi.getLearningLoop)
}

export function useActivityCatalog(kind) {
  return useTutorQuery(['activity-catalog', kind], () => tutorApi.getActivityCatalog(kind))
}

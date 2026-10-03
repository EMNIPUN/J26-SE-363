import tutorApi from '../services/tutorApi.js'
import { useTutorQuery } from './useTutorQuery.js'

export function useUpdatedCompetency(assessmentId) {
  return useTutorQuery(['updated-competency', assessmentId], () => tutorApi.getUpdatedCompetency(assessmentId), {
    enabled: Boolean(assessmentId),
    retry: false,
  })
}

export function useAssessmentHistory() {
  return useTutorQuery(['assessment-history'], tutorApi.getAssessmentHistory)
}

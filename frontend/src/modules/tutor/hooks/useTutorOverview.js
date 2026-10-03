import tutorApi from '../services/tutorApi.js'
import { useTutorQuery } from './useTutorQuery.js'

export function useTutorContext() {
  return useTutorQuery(['context'], tutorApi.getTutorContext)
}

export function useRequiredKnowledge() {
  return useTutorQuery(['required-knowledge'], tutorApi.getRequiredKnowledge)
}

export function useCompetencies() {
  return useTutorQuery(['competencies'], tutorApi.getCompetencies)
}

export function useKnowledgeGaps() {
  return useTutorQuery(['knowledge-gaps'], tutorApi.getKnowledgeGaps)
}

export function useRecommendation() {
  return useTutorQuery(['recommendation'], tutorApi.getRecommendation)
}

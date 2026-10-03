import { useMutation } from '@tanstack/react-query'
import tutorApi from '../services/tutorApi.js'
import { useInvalidateTutorData, useTutorQuery } from './useTutorQuery.js'

export function useActivity(activityId) {
  return useTutorQuery(['activity', activityId], () => tutorApi.getActivity(activityId), {
    enabled: Boolean(activityId),
  })
}

// New evidence changes competencies, gaps, guidance and the recommendation,
// so a completed sync refreshes every tutor query.
export function useSyncActivity(activityId) {
  const invalidateTutorData = useInvalidateTutorData()
  return useMutation({
    mutationFn: () => tutorApi.syncActivityResult(activityId),
    onSuccess: (data) => {
      if (data.status === 'completed') invalidateTutorData()
    },
  })
}
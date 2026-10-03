import { useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useScope } from '@/shared/context/useScope.js'

// Every tutor query key starts with ['tutor', teamCode] so switching teams
// refetches, and new assessment evidence can invalidate all tutor data at once.
export function useTutorTeam() {
  const { selectedGroup } = useScope()
  return selectedGroup?.code ?? null
}

export function tutorQueryKey(team, key = []) {
  return ['tutor', team, ...key]
}

export function useTutorQuery(key, queryFn, { enabled = true, ...options } = {}) {
  const team = useTutorTeam()
  return useQuery({
    queryKey: tutorQueryKey(team, key),
    queryFn,
    enabled: Boolean(team) && enabled,
    ...options,
  })
}

export function useInvalidateTutorData() {
  const queryClient = useQueryClient()
  const team = useTutorTeam()
  return useCallback(() => queryClient.invalidateQueries({ queryKey: tutorQueryKey(team) }), [queryClient, team])
}

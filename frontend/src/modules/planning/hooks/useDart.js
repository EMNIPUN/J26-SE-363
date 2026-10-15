import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { dartService } from '../services/dartService.js'

export function useDartCases(params = {}, enabled = true) {
  return useQuery({
    queryKey: ['dart-cases', params],
    queryFn: () => dartService.getCases(params),
    enabled,
    refetchInterval: 30000,
  })
}

export function useDartCase(caseRef) {
  return useQuery({
    queryKey: ['dart-case', caseRef],
    queryFn: () => dartService.getCase(caseRef),
    enabled: Boolean(caseRef),
  })
}

export function useArbitrate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload) => dartService.arbitrate(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dart-cases'] })
    },
  })
}

export function useResolveCase() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ caseRef, body }) => dartService.resolveCase(caseRef, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dart-cases'] })
    },
  })
}

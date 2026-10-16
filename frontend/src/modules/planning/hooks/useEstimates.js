import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { estimationService } from '../services/estimationService.js'

const KEY = ['estimates']

export function useEstimates(enabled = true) {
  return useQuery({
    queryKey: KEY,
    queryFn: () => estimationService.listEstimates(),
    enabled,
  })
}

export function useSaveEstimate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body) => estimationService.saveEstimate(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}

export function useConfirmEstimate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (storyRef) => estimationService.confirmEstimate(storyRef),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY })
      qc.invalidateQueries({ queryKey: ['backlog-items'] })
    },
  })
}

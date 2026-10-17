import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { decompositionService } from '../services/decompositionService.js'

export function useStories(enabled = true) {
  return useQuery({
    queryKey: ['planning-stories'],
    queryFn: () => decompositionService.listStories(),
    enabled,
  })
}

export function useCreateStory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (story) => decompositionService.createStory(story),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['planning-stories'] }),
  })
}

export function useUpdateStory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ ref, patch }) => decompositionService.updateStory(ref, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['planning-stories'] }),
  })
}

export function useCreateStoryTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ ref, task }) => decompositionService.createTask(ref, task),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['planning-stories'] }),
  })
}

export function useDeleteStory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ref) => decompositionService.deleteStory(ref),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['planning-stories'] }),
  })
}

export function useAnalyzeDecomposition() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ requirement, stories, threshold = 75 }) =>
      decompositionService.analyzeDecomposition({ requirement, stories, threshold }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['decomposition-results'] }),
  })
}

export function useDecompositionResults(enabled = true) {
  return useQuery({
    queryKey: ['decomposition-results'],
    queryFn: () => decompositionService.getResults(),
    enabled,
  })
}

export function useDecompositionHistory(requirementRef) {
  return useQuery({
    queryKey: ['decomposition-history', requirementRef],
    queryFn: () => decompositionService.getHistory(requirementRef),
    enabled: Boolean(requirementRef),
  })
}

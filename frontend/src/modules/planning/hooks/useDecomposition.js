import { useMutation, useQuery } from '@tanstack/react-query'
import { decompositionService } from '../services/decompositionService.js'

export function useStories(enabled = true) {
  return useQuery({
    queryKey: ['planning-stories'],
    queryFn: () => decompositionService.listStories(),
    enabled,
  })
}

export function useCreateStory() {
  return useMutation({
    mutationFn: (story) => decompositionService.createStory(story),
  })
}

export function useUpdateStory() {
  return useMutation({
    mutationFn: ({ ref, patch }) => decompositionService.updateStory(ref, patch),
  })
}

export function useDeleteStory() {
  return useMutation({
    mutationFn: (ref) => decompositionService.deleteStory(ref),
  })
}

export function useAnalyzeDecomposition() {
  return useMutation({
    mutationFn: ({ requirement, stories, threshold = 75 }) =>
      decompositionService.analyzeDecomposition({ requirement, stories, threshold }),
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

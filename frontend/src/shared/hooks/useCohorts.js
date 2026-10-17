import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { cohortService } from '../services/cohortService.js'
import { toast } from 'sonner'

export function useBatches(params) {
  return useQuery({
    queryKey: ['batches', params],
    queryFn: () => cohortService.getBatches(params),
  })
}

export function useCreateBatch() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload) => cohortService.createBatch(payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['batches'] })
      toast.success(`Batch ${data.name || data.id} created successfully!`)
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to create batch.')
    },
  })
}

export function useProjects(batchId) {
  return useQuery({
    queryKey: ['projects', batchId],
    queryFn: () => cohortService.getProjects(batchId ? { batch_id: batchId } : {}),
    enabled: Boolean(batchId),
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload) => cohortService.createProject(payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      toast.success(`Project "${data.name}" registered successfully!`)
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to create project.')
    },
  })
}

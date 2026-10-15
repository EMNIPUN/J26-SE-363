import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { sprintService } from '../services/sprintService.js'

const KEY = ['sprint-tasks']

export function useSprintTasks(enabled = true) {
  return useQuery({
    queryKey: KEY,
    queryFn: () => sprintService.listTasks(),
    enabled,
  })
}

export function useCreateSprintTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body) => sprintService.createTask(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}

export function useUpdateSprintTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ ref, patch }) => sprintService.updateTask(ref, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}

export function useDeleteSprintTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ref) => sprintService.deleteTask(ref),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { sprintService } from '../services/sprintService.js'

const KEY = ['backlog-items']

export function useBacklogItems(enabled = true) {
  return useQuery({
    queryKey: KEY,
    queryFn: () => sprintService.listItems(),
    enabled,
  })
}

export function useCreateBacklogItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body) => sprintService.createItem(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}

export function useUpdateBacklogItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, patch }) => sprintService.updateItem(id, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}

export function useDeleteBacklogItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => sprintService.deleteItem(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}

// Backward compat exports
export const useSprintTasks = useBacklogItems
export const useCreateSprintTask = useCreateBacklogItem
export const useUpdateSprintTask = useUpdateBacklogItem
export const useDeleteSprintTask = useDeleteBacklogItem

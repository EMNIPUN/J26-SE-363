import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { planningService } from '../services/planningService.js'

/**
 * TanStack Query Hook: Retrieve projects with automatic caching
 * @param {Object} [params]
 */
export function useProjects(params) {
  return useQuery({
    queryKey: ['projects', params],
    queryFn: () => planningService.getProjects(params),
  })
}

/**
 * TanStack Query Hook: Retrieve single project details
 * @param {string|number} projectId
 */
export function useProjectDetail(projectId) {
  return useQuery({
    queryKey: ['projects', projectId],
    queryFn: () => planningService.getProjectById(projectId),
    enabled: Boolean(projectId),
  })
}

/**
 * TanStack Mutation Hook: Create new task with automatic cache invalidation
 */
export function useCreateTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (taskData) => planningService.createTask(taskData),
    onSuccess: (_, variables) => {
      // Automatically invalidate and refresh related queries
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      if (variables?.projectId) {
        queryClient.invalidateQueries({ queryKey: ['tasks', variables.projectId] })
      }
    },
  })
}

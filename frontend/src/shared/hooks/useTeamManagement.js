import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { teamManagementService } from '../services/teamManagementService.js'
import { jobService } from '../services/jobService.js'
import { toast } from 'sonner'

export function useTeams(batchId) {
  return useQuery({
    queryKey: ['teams', batchId],
    queryFn: () => teamManagementService.getTeams(batchId ? { batch_id: batchId } : {}),
    enabled: Boolean(batchId),
  })
}

export function useTeamDetail(teamId) {
  return useQuery({
    queryKey: ['team-detail', teamId],
    queryFn: () => teamManagementService.getTeamDetail(teamId),
    enabled: Boolean(teamId),
  })
}

export function useBulkImportTeams() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload) => teamManagementService.bulkCreateTeams(payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['teams'] })
      if (data.errors && data.errors.length > 0) {
        toast.warning(
          `Imported ${data.created_count} teams with ${data.errors.length} skipped conflict(s).`
        )
      } else {
        toast.success(`Successfully imported ${data.created_count} teams!`)
      }
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to bulk-import teams.')
    },
  })
}

export function useAddTeamMember(teamId) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload) => teamManagementService.addMember(teamId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-detail', teamId] })
      queryClient.invalidateQueries({ queryKey: ['teams'] })
      toast.success('Team member added successfully!')
    },
    onError: (error) => {
      if (error.status === 409) {
        toast.error('Academic Rule Conflict: Student is already registered in another team in this batch.')
      } else {
        toast.error(error.message || 'Failed to add team member.')
      }
    },
  })
}

export function useRemoveTeamMember(teamId) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (studentId) => teamManagementService.removeMember(teamId, studentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-detail', teamId] })
      queryClient.invalidateQueries({ queryKey: ['teams'] })
      toast.success('Member removed from team.')
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to remove member.')
    },
  })
}

export function useTriggerAgentJob() {
  return useMutation({
    mutationFn: (payload) => jobService.publishJob(payload),
    onSuccess: (data) => {
      toast.success(`Agent job #${data.job_id} (${data.task_name}) enqueued!`)
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to trigger agent job.')
    },
  })
}

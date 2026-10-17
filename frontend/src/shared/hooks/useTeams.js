import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { teamService } from '../services/teamService.js'
import { showToast } from '../utils/toast.jsx'

export const teamKeys = {
  mine: ['teams', 'mine'],
  detail: (team) => ['teams', 'detail', team],
  invitations: ['invitations', 'mine'],
  lookup: (token) => ['invitations', 'lookup', token],
  sent: ['invitations', 'sent'],
  available: (term) => ['students', 'available', term],
}

export function useMyTeams({ enabled = true } = {}) {
  return useQuery({ queryKey: teamKeys.mine, queryFn: teamService.getMyTeams, enabled })
}

export function useTeam(team, { enabled = true } = {}) {
  return useQuery({
    queryKey: teamKeys.detail(team),
    queryFn: () => teamService.getTeam(team),
    enabled: Boolean(team) && enabled,
  })
}

export function useMyInvitations({ enabled = true } = {}) {
  return useQuery({
    queryKey: teamKeys.invitations,
    queryFn: teamService.getMyInvitations,
    enabled,
  })
}

/** Lecturers: the invitations they sent that are still waiting. */
export function useSentInvitations({ enabled = true } = {}) {
  return useQuery({ queryKey: teamKeys.sent, queryFn: teamService.getSentInvitations, enabled })
}

/** Lecturers: students of their institution with no team in this term. */
export function useAvailableStudents(term, { enabled = true } = {}) {
  return useQuery({
    queryKey: teamKeys.available(term),
    queryFn: () => teamService.getAvailableStudents(term),
    enabled: enabled && Boolean(term),
  })
}

export function useInvitationLookup(token) {
  return useQuery({
    queryKey: teamKeys.lookup(token),
    queryFn: () => teamService.lookupInvitation(token),
    enabled: Boolean(token),
    retry: false,
  })
}

// One helper for every action on a team: refresh what changed, report problems in a toast.
function useTeamAction(mutationFn, { success, refresh = () => [] } = {}) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    onSuccess: async (data, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: teamKeys.mine }),
        queryClient.invalidateQueries({ queryKey: teamKeys.invitations }),
        queryClient.invalidateQueries({ queryKey: teamKeys.sent }),
        queryClient.invalidateQueries({ queryKey: ['students'] }),
        ...refresh(variables).map((queryKey) => queryClient.invalidateQueries({ queryKey })),
      ])
      if (success) showToast.success(typeof success === 'function' ? success(data, variables) : success)
    },
    onError: (error) => showToast.error(error.message),
  })
}

const detailOf = (team) => [teamKeys.detail(team)]

export const useCreateTeam = () => useTeamAction(teamService.createTeam)

export const useUpdateTeam = (team) =>
  useTeamAction((updates) => teamService.updateTeam(team, updates), {
    success: 'Team updated',
    refresh: () => detailOf(team),
  })

export const useInviteToTeam = (team) =>
  useTeamAction((payload) => teamService.invite(team, payload), { refresh: () => detailOf(team) })

export const useResendInvitation = (team) =>
  useTeamAction((invitationId) => teamService.resendInvitation(team, invitationId), {
    success: 'Invitation sent again',
    refresh: () => detailOf(team),
  })

export const useWithdrawInvitation = (team) =>
  useTeamAction((invitationId) => teamService.withdrawInvitation(team, invitationId), {
    success: 'Invitation withdrawn',
    refresh: () => detailOf(team),
  })

export const useRemoveMember = (team) =>
  useTeamAction((userId) => teamService.removeMember(team, userId), {
    success: 'Done',
    refresh: () => detailOf(team),
  })

export const useOfferLeadership = (team) =>
  useTeamAction((toUserId) => teamService.offerLeadership(team, toUserId), {
    success: 'Leadership offered. They need to accept it.',
    refresh: () => detailOf(team),
  })

export const useRespondToLeadership = (team) =>
  useTeamAction(
    (accept) => (accept ? teamService.acceptLeadership(team) : teamService.declineLeadership(team)),
    {
      success: (_, accept) => (accept ? 'You are now the team leader' : 'Request declined'),
      refresh: () => detailOf(team),
    },
  )

export const useWithdrawLeadershipOffer = (team) =>
  useTeamAction(() => teamService.withdrawLeadershipOffer(team), {
    success: 'Offer withdrawn',
    refresh: () => detailOf(team),
  })

export const useAcceptInvitation = () =>
  useTeamAction(teamService.acceptInvitation, {
    success: (team) => `You joined ${team.name}`,
  })

export const useDeclineInvitation = () =>
  useTeamAction(teamService.declineInvitation, { success: 'Invitation declined' })

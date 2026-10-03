import { useMutation, useQueryClient } from '@tanstack/react-query'
import tutorApi from '../services/tutorApi.js'
import { tutorQueryKey, useTutorQuery, useTutorTeam } from './useTutorQuery.js'

const CONVERSATION_KEY = ['conversation']

export function useTutorConversation() {
  return useTutorQuery(CONVERSATION_KEY, tutorApi.getTutorConversation, { staleTime: Infinity })
}

export function useQuickActions() {
  return useTutorQuery(['quick-actions'], tutorApi.getQuickActions, { staleTime: Infinity })
}

export function useSendTutorMessage() {
  const queryClient = useQueryClient()
  const team = useTutorTeam()

  return useMutation({
    mutationFn: tutorApi.sendTutorMessage,
    onSuccess: ({ message, reply }) => {
      queryClient.setQueryData(tutorQueryKey(team, CONVERSATION_KEY), (previous = []) => [...previous, message, reply])
    },
  })
}

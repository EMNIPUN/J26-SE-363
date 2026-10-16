import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { sessionService } from '../services/sessionService.js'

const KEY = ['pipeline-session']

export function useActiveSession(enabled = true) {
  return useQuery({
    queryKey: [...KEY, 'active'],
    queryFn: () => sessionService.getActive(),
    enabled,
  })
}

export function useSessionDetail(id) {
  return useQuery({
    queryKey: [...KEY, id],
    queryFn: () => sessionService.getDetail(id),
    enabled: Boolean(id),
  })
}

export function useCreateSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => sessionService.create(),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}

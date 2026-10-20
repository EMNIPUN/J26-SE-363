import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { passportService } from '../services/passportService.js'

export const PASSPORTS_KEY = ['backlog-passports']
export const passportStoryKey = (ref) => ['backlog-passport', ref]

export function usePassports(enabled = true) {
  return useQuery({
    queryKey: PASSPORTS_KEY,
    queryFn: async () => {
      const res = await passportService.listPassports()
      const payload = res?.data ?? res
      // The API returns an envelope: { passports: [...] }.
      // Keep the hook's public value as an array for callers that iterate it.
      return Array.isArray(payload) ? payload : payload?.passports ?? []
    },
    enabled,
    staleTime: 30000,
  })
}

export function useStoryPassport(storyRef, enabled = true) {
  return useQuery({
    queryKey: passportStoryKey(storyRef),
    queryFn: async () => {
      if (!storyRef) return null
      try {
        const res = await passportService.getPassport(storyRef)
        const payload = res?.data ?? res
        return payload?.passport ?? payload ?? null
      } catch {
        return null
      }
    },
    enabled: Boolean(enabled && storyRef),
    staleTime: 30000,
  })
}

export function useEvaluatePassport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (storyRef) => passportService.evaluatePassport(storyRef),
    onSuccess: (data, storyRef) => {
      qc.invalidateQueries({ queryKey: PASSPORTS_KEY })
      if (storyRef) {
        qc.invalidateQueries({ queryKey: passportStoryKey(storyRef) })
      }
      qc.invalidateQueries({ queryKey: ['planning-stories'] })
      qc.invalidateQueries({ queryKey: ['backlog-items'] })
    },
  })
}

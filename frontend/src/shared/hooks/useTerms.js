import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { termService } from '../services/termService.js'

export const termKeys = { all: ['terms'] }

/** The academic terms a team can belong to, newest first. */
export function useTerms() {
  return useQuery({
    queryKey: termKeys.all,
    queryFn: termService.list,
    select: (terms) => terms.map((term) => term.name),
    staleTime: 5 * 60 * 1000,
  })
}

/** Adds a term to the list. Resolves with the stored name; a term that exists already is not an error. */
export function useCreateTerm() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (name) => {
      try {
        return (await termService.create(name)).name
      } catch (error) {
        if (error.code === 'term_exists') return name // someone added it first: use theirs
        throw error
      }
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: termKeys.all }),
  })
}

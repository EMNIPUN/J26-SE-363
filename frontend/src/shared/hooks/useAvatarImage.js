import { useQuery } from '@tanstack/react-query'
import apiClient from '@/shared/api/apiClient'

/**
 * A picture kept by the Core API (a path such as /users/<id>/avatar?v=...). Those need the
 * person's token, which an <img> tag cannot send, so the image is fetched and shown from memory.
 * Returns nothing for a web address or an empty value; those are shown directly.
 */
export function useAvatarImage(picture) {
  const isApiPath = typeof picture === 'string' && picture.startsWith('/')
  return useQuery({
    queryKey: ['avatar', picture],
    enabled: isApiPath,
    // The path ends in ?v=<time of upload>, so a new upload is a new address and a new fetch.
    staleTime: Infinity,
    gcTime: 30 * 60 * 1000,
    retry: false,
    queryFn: async () => URL.createObjectURL(await apiClient.get(picture, { responseType: 'blob' })),
  }).data
}

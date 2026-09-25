import { QueryClient } from '@tanstack/react-query'

/**
 * Global TanStack QueryClient Configuration
 *
 * Production Defaults:
 * - 5-minute staleTime for aggressive automatic caching and deduplication
 * - Intelligent retry (avoids retrying 401/403/404 errors)
 * - Automatic background revalidation on window focus and network reconnect
 * - Mutation safety (no automatic mutation retries to prevent duplicate writes)
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000,    // 10 minutes cache garbage collection
      retry: (failureCount, error) => {
        // Do not retry on client-side authentication or client errors
        if (error?.status === 401 || error?.status === 403 || error?.status === 404) {
          return false
        }
        return failureCount < 2
      },
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: false, // Prevent accidental duplicate POST/PATCH/DELETE mutations
    },
  },
})

export default queryClient

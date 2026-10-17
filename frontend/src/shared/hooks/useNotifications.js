import { keepPreviousData, useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { notificationService } from '../services/notificationService.js'
import { showToast } from '../utils/toast.jsx'

export const notificationKeys = {
  all: ['notifications'],
  recent: ['notifications', 'recent'],
  page: (unreadOnly) => ['notifications', 'page', unreadOnly],
  preferences: ['notifications', 'preferences'],
}

const RECENT = 15
const POLL_MS = 30 * 1000

/** What the bell shows: the newest few and how many are unread. Checked every 30 seconds while the page is open. */
export function useRecentNotifications({ enabled = true } = {}) {
  return useQuery({
    queryKey: notificationKeys.recent,
    queryFn: () => notificationService.list({ limit: RECENT }),
    enabled,
    refetchInterval: POLL_MS,
    refetchOnWindowFocus: true,
    placeholderData: keepPreviousData,
  })
}

/** The full list, a page at a time, optionally only the unread ones. */
export function useNotificationPages(unreadOnly) {
  return useInfiniteQuery({
    queryKey: notificationKeys.page(unreadOnly),
    queryFn: ({ pageParam }) => notificationService.list({ limit: 30, before: pageParam }),
    initialPageParam: undefined,
    getNextPageParam: (last) => last.next_before ?? undefined,
    select: (data) => ({
      items: data.pages.flatMap((page) => page.items).filter((item) => !unreadOnly || !item.read),
      unread: data.pages[0]?.unread_count ?? 0,
    }),
    refetchInterval: POLL_MS,
  })
}

function useNotificationAction(mutationFn) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: notificationKeys.all }),
    onError: (error) => showToast.error(error.message),
  })
}

export const useMarkRead = () => useNotificationAction(notificationService.markRead)
export const useMarkAllRead = () => useNotificationAction(notificationService.markAllRead)
export const useDismissNotification = () => useNotificationAction(notificationService.dismiss)

export function useNotificationPreferences() {
  return useQuery({ queryKey: notificationKeys.preferences, queryFn: notificationService.getPreferences })
}

export function useSetNotificationPreference() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ category, enabled }) => notificationService.setPreferences({ [category]: enabled }),
    onSuccess: (data) => queryClient.setQueryData(notificationKeys.preferences, data),
    onError: (error) => showToast.error(error.message),
  })
}

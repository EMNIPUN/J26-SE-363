import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Bell, CheckCheck, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { useMarkAllRead, useNotificationPages } from '../../hooks/useNotifications.js'
import EmptyState from '../../components/EmptyState.jsx'
import NotificationItem from '../../components/NotificationItem.jsx'
import PageHeader from '../../components/PageHeader.jsx'

const FILTERS = [
  { key: false, label: 'All' },
  { key: true, label: 'Unread' },
]

/** Everything the application has told the person, newest first. */
export default function NotificationsPage() {
  const [unreadOnly, setUnreadOnly] = useState(false)
  const pages = useNotificationPages(unreadOnly)
  const markAll = useMarkAllRead()
  const items = pages.data?.items ?? []
  const unread = pages.data?.unread ?? 0

  return (
    <div className="mx-auto grid w-full max-w-3xl gap-6">
      <PageHeader
        title="Notifications"
        description={unread > 0 ? `${unread} unread` : 'You are all caught up.'}
        actions={
          <>
            <Button asChild variant="outline" size="sm">
              <Link to="/profile/notifications">
                <Settings aria-hidden="true" />
                Settings
              </Link>
            </Button>
            {unread > 0 && (
              <Button size="sm" variant="outline" loading={markAll.isPending} onClick={() => markAll.mutate()}>
                <CheckCheck aria-hidden="true" />
                Mark all read
              </Button>
            )}
          </>
        }
      />

      <div className="-mt-2 flex gap-1" role="tablist" aria-label="Filter">
        {FILTERS.map(({ key, label }) => (
          <button
            key={label}
            type="button"
            role="tab"
            aria-selected={unreadOnly === key}
            onClick={() => setUnreadOnly(key)}
            className={cn(
              'cursor-pointer rounded-md px-3 py-1.5 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring',
              unreadOnly === key ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted/60',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {pages.isPending && <Skeleton className="h-40 w-full" aria-busy="true" />}
      {pages.isError && <p className="text-sm text-destructive">Notifications could not be loaded.</p>}
      {pages.isSuccess && items.length === 0 && (
        <EmptyState
          icon={Bell}
          title={unreadOnly ? 'Nothing unread' : 'No notifications yet'}
          description="Invitations, leadership offers and team activity show up here."
        />
      )}
      {items.length > 0 && (
        <Card className="gap-0 overflow-hidden p-0">
          <ul className="divide-y divide-border/60">
            {items.map((item) => (
              <NotificationItem key={item.id} item={item} />
            ))}
          </ul>
          {pages.hasNextPage && (
            <div className="border-t border-border p-3 text-center">
              <Button variant="ghost" size="sm" loading={pages.isFetchingNextPage} onClick={() => pages.fetchNextPage()}>
                Load older
              </Button>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}

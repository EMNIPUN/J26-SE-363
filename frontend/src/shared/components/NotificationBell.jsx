import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Bell, CheckCheck, CheckCircle2, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useMarkAllRead, useRecentNotifications } from '../hooks/useNotifications.js'
import NotificationItem from './NotificationItem.jsx'

/**
 * The bell in the top bars. Shows the person's real notifications (never samples): what happened,
 * with Accept and Decline where an answer is wanted. Everything the application tells a person
 * comes from one place on the server (the Notifier); this only shows it.
 */
export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const recent = useRecentNotifications()
  const markAll = useMarkAllRead()
  const items = recent.data?.items ?? []
  const unread = recent.data?.unread_count ?? 0

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative h-9 w-9 text-muted-foreground hover:text-foreground"
          aria-label={`Notifications, ${unread} unread`}
        >
          <Bell className="h-4 w-4" />
          {unread > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold leading-none text-primary-foreground">
              {unread > 9 ? '9+' : unread}
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={8}
        className="w-[360px] overflow-hidden rounded-xl border-border bg-popover p-0 shadow-2xl sm:w-[400px]"
      >
        <div className="flex items-center justify-between border-b border-border bg-muted/20 px-3.5 py-3">
          <span className="text-sm font-semibold tracking-tight text-foreground">Notifications</span>
          <div className="flex items-center gap-1">
            {unread > 0 && (
              <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs text-muted-foreground" loading={markAll.isPending} onClick={() => markAll.mutate()}>
                <CheckCheck className="h-3.5 w-3.5" aria-hidden="true" />
                Mark all read
              </Button>
            )}
            <Button asChild variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground">
              <Link to="/profile/notifications" aria-label="Notification settings" onClick={() => setOpen(false)}>
                <Settings className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </div>
        </div>

        <div className="max-h-[420px] overflow-y-auto">
          {recent.isError && (
            <p className="p-6 text-center text-xs text-muted-foreground">Notifications could not be loaded.</p>
          )}
          {recent.isSuccess && items.length === 0 && (
            <div className="flex flex-col items-center justify-center p-8 text-center">
              <CheckCircle2 className="mb-2 h-8 w-8 stroke-[1.5] text-muted-foreground/50" />
              <p className="text-xs font-medium text-foreground">You are all caught up</p>
              <p className="mt-0.5 text-[11px] text-muted-foreground">New activity shows up here.</p>
            </div>
          )}
          {items.length > 0 && (
            <ul className="divide-y divide-border/40">
              {items.map((item) => (
                <NotificationItem key={item.id} item={item} compact onNavigate={() => setOpen(false)} />
              ))}
            </ul>
          )}
        </div>

        <div className="border-t border-border px-3.5 py-2.5">
          <Link to="/notifications" onClick={() => setOpen(false)} className="text-xs font-medium text-primary hover:underline">
            View all notifications
          </Link>
        </div>
      </PopoverContent>
    </Popover>
  )
}

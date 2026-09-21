import { useState } from 'react'
import {
  Bell,
  CheckCheck,
  Trash2,
  Calendar,
  FileText,
  Sparkles,
  CheckCircle2,
  X,
  Plus
} from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { showToast } from '@/shared/utils/toast.jsx'

const INITIAL_NOTIFICATIONS = [
  {
    id: 'n-1',
    title: 'Milestone 2 Defense Scheduled',
    description: 'Your presentation is confirmed for Friday at 10:00 AM with panel examiners.',
    time: '10m ago',
    read: false,
    type: 'calendar',
  },
  {
    id: 'n-2',
    title: 'Literature Review Feedback',
    description: 'Supervisor Dr. Perera added 3 actionable review comments to Section 2.',
    time: '45m ago',
    read: false,
    type: 'feedback',
  },
  {
    id: 'n-3',
    title: 'AI Methodology Check Complete',
    description: 'Structure and citation verification finished with 0 discrepancies found.',
    time: '2h ago',
    read: false,
    type: 'ai',
  },
  {
    id: 'n-4',
    title: 'Scheduled System Maintenance',
    description: 'Routine platform updates tonight from 2:00 AM to 3:00 AM UTC.',
    time: '1d ago',
    read: true,
    type: 'system',
  },
]

function getNotificationIcon(type) {
  switch (type) {
    case 'calendar':
      return <Calendar className="h-4 w-4 text-primary shrink-0" />
    case 'feedback':
      return <FileText className="h-4 w-4 text-primary shrink-0" />
    case 'ai':
      return <Sparkles className="h-4 w-4 text-amber-500 dark:text-amber-400 shrink-0" />
    case 'system':
    default:
      return <Bell className="h-4 w-4 text-muted-foreground shrink-0" />
  }
}

export default function NotificationDropdown() {
  const [notifications, setNotifications] = useState(INITIAL_NOTIFICATIONS)
  const [filter, setFilter] = useState('all') // 'all' | 'unread'
  const [open, setOpen] = useState(false)

  const unreadCount = notifications.filter((n) => !n.read).length

  const filteredNotifications = notifications.filter((n) => {
    if (filter === 'unread') return !n.read
    return true
  })

  const handleMarkAllRead = () => {
    if (unreadCount === 0) return
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
    showToast.success('All caught up!', {
      description: 'All notifications have been marked as read.',
    })
  }

  const handleClearAll = () => {
    if (notifications.length === 0) return
    setNotifications([])
    showToast.info('Notifications cleared', {
      description: 'All activity records have been cleared.',
    })
  }

  const handleItemClick = (item) => {
    if (!item.read) {
      setNotifications((prev) =>
        prev.map((n) => (n.id === item.id ? { ...n, read: true } : n)),
      )
    }
    showToast.info(item.title, {
      description: item.description,
    })
  }

  const handleDismissItem = (e, id) => {
    e.stopPropagation()
    setNotifications((prev) => prev.filter((n) => n.id !== id))
  }

  const handleSimulateNotification = () => {
    const newId = `n-${Date.now()}`
    const mockTypes = ['ai', 'feedback', 'calendar', 'system']
    const randomType = mockTypes[Math.floor(Math.random() * mockTypes.length)]
    const newNotification = {
      id: newId,
      title: randomType === 'ai' ? 'AI Citation Scan Updated' : 'Supervisor Review Received',
      description: 'New progress update was logged for your research workspace.',
      time: 'Just now',
      read: false,
      type: randomType,
    }

    setNotifications((prev) => [newNotification, ...prev])

    // Fire matching professional toast
    if (randomType === 'ai') {
      showToast.ai(newNotification.title, {
        description: newNotification.description,
      })
    } else {
      showToast.info(newNotification.title, {
        description: newNotification.description,
      })
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative h-9 w-9 text-muted-foreground hover:text-foreground cursor-pointer transition-transform active:scale-95"
          aria-label={`Notifications, ${unreadCount} unread`}
        >
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span className="absolute top-1.5 right-1.5 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary" />
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={8}
        className="w-[360px] sm:w-[400px] p-0 shadow-2xl border-border bg-popover rounded-xl overflow-hidden"
      >
        {/* Header */}
        <div className="p-3.5 border-b border-border bg-muted/20">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold tracking-tight text-foreground">
                Notifications
              </span>
              {unreadCount > 0 ? (
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 font-normal">
                  {unreadCount} new
                </Badge>
              ) : (
                <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 font-normal text-muted-foreground">
                  Caught up
                </Badge>
              )}
            </div>

            <div className="flex items-center gap-1">
              {unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleMarkAllRead}
                  className="h-7 px-2 text-[11px] text-muted-foreground hover:text-foreground gap-1 cursor-pointer"
                  title="Mark all as read"
                >
                  <CheckCheck className="h-3.5 w-3.5" />
                  <span>Mark read</span>
                </Button>
              )}

              {notifications.length > 0 && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleClearAll}
                  className="h-7 w-7 text-muted-foreground hover:text-destructive cursor-pointer"
                  title="Clear all notifications"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setFilter('all')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                filter === 'all'
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
              }`}
            >
              All ({notifications.length})
            </button>
            <button
              type="button"
              onClick={() => setFilter('unread')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                filter === 'unread'
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
              }`}
            >
              Unread ({unreadCount})
            </button>
          </div>
        </div>

        {/* Notification List */}
        <div className="max-h-[340px] overflow-y-auto column-scroll-contain divide-y divide-border/40">
          {filteredNotifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-center text-muted-foreground">
              <CheckCircle2 className="h-8 w-8 mb-2 text-muted-foreground/50 stroke-[1.5]" />
              <p className="text-xs font-medium text-foreground">No notifications</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                {filter === 'unread'
                  ? 'You have read all pending notifications.'
                  : 'Your inbox is completely clear.'}
              </p>
            </div>
          ) : (
            filteredNotifications.map((item) => (
              <div
                key={item.id}
                onClick={() => handleItemClick(item)}
                className={`relative p-3.5 transition-colors cursor-pointer group flex items-start gap-3 ${
                  item.read ? 'hover:bg-muted/40' : 'bg-muted/15 hover:bg-muted/50'
                }`}
              >
                {/* Type Icon Container */}
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted border border-border/60 shadow-xs mt-0.5">
                  {getNotificationIcon(item.type)}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 pr-4">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <p
                      className={`text-xs leading-tight truncate ${
                        item.read ? 'font-normal text-foreground/90' : 'font-semibold text-foreground'
                      }`}
                    >
                      {item.title}
                    </p>
                    {!item.read && (
                      <span className="h-1.5 w-1.5 rounded-full bg-primary shrink-0" />
                    )}
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
                    {item.description}
                  </p>
                  <span className="text-[10px] text-muted-foreground/70 mt-1 block">
                    {item.time}
                  </span>
                </div>

                {/* Single Dismiss Button (appears on hover) */}
                <button
                  type="button"
                  onClick={(e) => handleDismissItem(e, item.id)}
                  aria-label="Dismiss notification"
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-1 text-muted-foreground hover:text-foreground rounded cursor-pointer absolute top-3 right-3"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-2 border-t border-border bg-muted/20 flex items-center justify-between">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleSimulateNotification}
            className="h-7 px-2 text-[11px] text-muted-foreground hover:text-foreground gap-1.5 cursor-pointer w-full justify-center"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Simulate New Notification (Test Toast)</span>
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}

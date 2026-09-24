import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search,
  LayoutDashboard,
  Calendar,
  BarChart3,
  Sparkles,
  ShieldAlert,
  Settings,
  Sun,
  Moon,
  Bell,
  HelpCircle,
  ArrowRight
} from 'lucide-react'
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { useTheme } from '@/shared/theme/useTheme.js'
import { useConfirm } from '@/shared/utils/useConfirm.js'
import { showToast } from '@/shared/utils/toast.jsx'

export default function CommandPalette({ open, onOpenChange }) {
  const [query, setQuery] = useState('')
  const navigate = useNavigate()
  const { theme, setTheme } = useTheme()
  const confirm = useConfirm()

  // Listen for global keyboard shortcut (Cmd+K / Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        onOpenChange((prev) => {
          if (!prev) setQuery('')
          return !prev
        })
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onOpenChange])

  const handleOpenChange = (nextOpen) => {
    if (!nextOpen) setQuery('')
    onOpenChange(nextOpen)
  }

  const COMMAND_SECTIONS = [
    {
      heading: 'Navigation & Portals',
      items: [
        { id: 'nav-overview', title: 'Dashboard Overview', icon: LayoutDashboard, path: '/app' },
        { id: 'nav-admin', title: 'Admin Console', icon: Settings, path: '/admin/users' },
        { id: 'nav-planning', title: 'Planning & Milestones', icon: Calendar, path: '/planning' },
        { id: 'nav-perf', title: 'Performance Analytics', icon: BarChart3, path: '/performance' },
        { id: 'nav-tutor', title: 'AI Research Tutor', icon: Sparkles, path: '/tutor' },
        { id: 'nav-sec', title: 'Security & Compliance', icon: ShieldAlert, path: '/security' },
      ],
    },
    {
      heading: 'Quick Actions & Tools',
      items: [
        {
          id: 'action-theme',
          title: theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark / Black Theme',
          icon: theme === 'dark' ? Sun : Moon,
          action: () => {
            const next = theme === 'dark' ? 'light' : 'dark'
            setTheme(next)
            showToast.info(`Theme set to ${next}`)
          },
        },
        {
          id: 'action-confirm-test',
          title: 'Test Global Confirmation Modal',
          icon: HelpCircle,
          action: async () => {
            onOpenChange(false)
            const ok = await confirm({
              title: 'Test Global Confirmation Popup',
              description: 'This is triggered imperatively using useConfirm() with 0 boilerplate.',
              confirmText: 'Acknowledge',
              cancelText: 'Dismiss',
              tone: 'default',
            })
            if (ok) {
              showToast.success('Confirmed!', { description: 'You confirmed the global popup.' })
            }
          },
        },
        {
          id: 'action-notif',
          title: 'Simulate Notification Alert',
          icon: Bell,
          action: () => {
            showToast.ai('New Research Alert', {
              description: 'Supervisor published a review for your milestone submission.',
            })
          },
        },
      ],
    },
  ]

  const filteredSections = COMMAND_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) =>
      item.title.toLowerCase().includes(query.toLowerCase()),
    ),
  })).filter((section) => section.items.length > 0)

  const handleSelectItem = (item) => {
    handleOpenChange(false)
    if (item.path) {
      navigate(item.path)
    } else if (item.action) {
      item.action()
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        showCloseButton={false}
        className="p-0 gap-0 max-w-xl overflow-hidden border-border bg-card shadow-2xl rounded-xl sm:max-w-xl"
      >
        <DialogTitle className="sr-only">Command Palette</DialogTitle>
        <DialogDescription className="sr-only">
          Quickly search modules, portals, and trigger actions.
        </DialogDescription>

        {/* Search Input Header */}
        <div className="flex items-center px-4 border-b border-border bg-muted/20 h-12">
          <Search className="h-4 w-4 text-muted-foreground mr-2 shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or search portals..."
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none"
            autoFocus
          />
          <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border border-border bg-muted/60 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-3 column-scroll-contain">
          {filteredSections.length === 0 ? (
            <div className="p-8 text-center text-xs text-muted-foreground">
              No results found for &ldquo;{query}&rdquo;.
            </div>
          ) : (
            filteredSections.map((section) => (
              <div key={section.heading} className="space-y-1">
                <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/80">
                  {section.heading}
                </div>
                <div className="space-y-0.5">
                  {section.items.map((item) => {
                    const Icon = item.icon
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => handleSelectItem(item)}
                        className="w-full flex items-center justify-between px-3 py-2 text-xs rounded-lg text-foreground hover:bg-muted/70 transition-colors group cursor-pointer text-left active:scale-[0.99]"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-muted border border-border/40 text-muted-foreground group-hover:text-foreground">
                            <Icon className="h-3.5 w-3.5" />
                          </div>
                          <span className="truncate font-medium">{item.title}</span>
                        </div>
                        <ArrowRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0 transition-all shrink-0" />
                      </button>
                    )
                  })}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer Hint */}
        <div className="px-4 py-2 border-t border-border bg-muted/30 flex items-center justify-between text-[11px] text-muted-foreground">
          <div className="flex items-center gap-2">
            <span>Navigation</span>
            <kbd className="px-1 py-0.5 rounded border border-border bg-muted text-[10px]">↵</kbd>
          </div>
          <div className="flex items-center gap-1">
            <span>MENTOR Command Palette</span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

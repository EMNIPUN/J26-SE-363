import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Sun, Moon, Laptop, ArrowRight, CornerDownLeft } from 'lucide-react'
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { useTheme } from '@/shared/theme/useTheme.js'
import { showToast } from '@/shared/utils/toast.jsx'
import { useAuth } from '../auth/useAuth.js'
import { useScope } from '../context/useScope.js'
import { getNavForRole } from '../layout/navConfig.js'

function buildPageItems(sections) {
  return sections.flatMap((section) => {
    if (section.children?.length) {
      return section.children.map((child) => ({
        id: child.to,
        title: child.label === 'Dashboard' ? `${section.label} dashboard` : child.label,
        hint: section.label,
        icon: section.icon,
        path: child.to,
      }))
    }
    return [{ id: section.to, title: section.label, icon: section.icon, path: section.to }]
  })
}

export default function CommandPalette({ open, onOpenChange }) {
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const navigate = useNavigate()
  const { setTheme } = useTheme()
  const { user } = useAuth()
  const { selectedGroup } = useScope()

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        onOpenChange((prev) => {
          if (!prev) {
            setQuery('')
            setActiveIndex(0)
          }
          return !prev
        })
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onOpenChange])

  const handleOpenChange = (nextOpen) => {
    if (!nextOpen) {
      setQuery('')
      setActiveIndex(0)
    }
    onOpenChange(nextOpen)
  }

  const sections = useMemo(() => {
    const nav = user ? getNavForRole(user.role, selectedGroup?.code) : []
    const applyTheme = (next, label) => () => {
      setTheme(next)
      showToast.info(`Theme set to ${label}`)
    }
    return [
      { heading: 'Pages', items: buildPageItems(nav) },
      {
        heading: 'Appearance',
        items: [
          { id: 'theme-light', title: 'Use light theme', icon: Sun, action: applyTheme('light', 'light') },
          { id: 'theme-dark', title: 'Use dark theme', icon: Moon, action: applyTheme('dark', 'dark') },
          { id: 'theme-system', title: 'Match system theme', icon: Laptop, action: applyTheme('system', 'system') },
        ],
      },
    ]
  }, [user, selectedGroup?.code, setTheme])

  const filteredSections = useMemo(() => {
    const q = query.trim().toLowerCase()
    let index = 0
    return sections
      .map((section) => ({
        ...section,
        items: section.items.filter(
          (item) =>
            !q ||
            item.title.toLowerCase().includes(q) ||
            item.hint?.toLowerCase().includes(q),
        ),
      }))
      .filter((section) => section.items.length > 0)
      .map((section) => ({
        ...section,
        items: section.items.map((item) => ({ ...item, index: index++ })),
      }))
  }, [sections, query])

  const flatItems = useMemo(() => filteredSections.flatMap((s) => s.items), [filteredSections])
  const safeIndex = Math.min(activeIndex, Math.max(flatItems.length - 1, 0))

  const handleSelectItem = (item) => {
    handleOpenChange(false)
    if (item.path) {
      navigate(item.path)
    } else if (item.action) {
      item.action()
    }
  }

  const handleInputKeyDown = (e) => {
    if (!flatItems.length) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((safeIndex + 1) % flatItems.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((safeIndex - 1 + flatItems.length) % flatItems.length)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      handleSelectItem(flatItems[safeIndex])
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        showCloseButton={false}
        className="p-0 gap-0 max-w-xl overflow-hidden border-border bg-card shadow-2xl rounded-xl sm:max-w-xl"
      >
        <DialogTitle className="sr-only">Search pages and actions</DialogTitle>
        <DialogDescription className="sr-only">
          Type to filter, use the arrow keys to move, and press Enter to open.
        </DialogDescription>

        <div className="flex items-center px-4 border-b border-border h-12">
          <Search className="h-4 w-4 text-muted-foreground mr-2 shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setActiveIndex(0)
            }}
            onKeyDown={handleInputKeyDown}
            placeholder="Search pages, e.g. “sprint” or “chat”…"
            aria-label="Search pages and actions"
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none"
            autoFocus
          />
          <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border border-border bg-muted/60 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
            ESC
          </kbd>
        </div>

        <div className="max-h-[22rem] overflow-y-auto p-2 space-y-3 column-scroll-contain" role="listbox">
          {filteredSections.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              No results for &ldquo;{query}&rdquo;. Try a page name like &ldquo;Dashboard&rdquo;.
            </div>
          ) : (
            filteredSections.map((section) => (
              <div key={section.heading} className="space-y-1">
                <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/80">
                  {section.heading}
                </div>
                <div className="space-y-0.5">
                  {section.items.map((item) => {
                    const itemIndex = item.index
                    const isActive = itemIndex === safeIndex
                    const Icon = item.icon
                    return (
                      <button
                        key={item.id}
                        type="button"
                        role="option"
                        aria-selected={isActive}
                        onClick={() => handleSelectItem(item)}
                        onMouseMove={() => !isActive && setActiveIndex(itemIndex)}
                        className={`w-full flex items-center justify-between px-3 py-2 text-sm rounded-lg text-foreground transition-colors cursor-pointer text-left ${
                          isActive ? 'bg-accent text-accent-foreground' : ''
                        }`}
                      >
                        <span className="flex items-center gap-2.5 min-w-0">
                          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-muted border border-border/40 text-muted-foreground">
                            {Icon && <Icon className="h-3.5 w-3.5" />}
                          </span>
                          <span className="truncate font-medium">{item.title}</span>
                          {item.hint && (
                            <span className="hidden sm:inline truncate text-xs text-muted-foreground">
                              {item.hint}
                            </span>
                          )}
                        </span>
                        <ArrowRight
                          className={`h-3.5 w-3.5 shrink-0 text-muted-foreground transition-all ${
                            isActive ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-1'
                          }`}
                        />
                      </button>
                    )
                  })}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="px-4 py-2 border-t border-border bg-muted/30 flex items-center gap-4 text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <kbd className="px-1 py-0.5 rounded border border-border bg-muted text-[10px]">↑</kbd>
            <kbd className="px-1 py-0.5 rounded border border-border bg-muted text-[10px]">↓</kbd>
            to move
          </span>
          <span className="flex items-center gap-1.5">
            <kbd className="px-1 py-0.5 rounded border border-border bg-muted text-[10px]">
              <CornerDownLeft className="h-2.5 w-2.5" />
            </kbd>
            to open
          </span>
        </div>
      </DialogContent>
    </Dialog>
  )
}

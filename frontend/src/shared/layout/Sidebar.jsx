import { useState, useEffect, useRef } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { ChevronDown } from 'lucide-react'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'

function isSectionActive(section, pathname) {
  if (section.to) {
    if (section.to === '/student' || section.to === '/instructor' || section.to === '/admin') {
      return pathname === section.to
    }
    return pathname === section.to || pathname.startsWith(section.to + '/')
  }
  return (section.children ?? []).some(
    (c) => pathname === c.to || pathname.startsWith(c.to + '/'),
  )
}

function CollapsedSimpleItem({ section, active, onNavigate }) {
  const Icon = section.icon
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <NavLink
          to={section.to}
          onClick={onNavigate}
          className={`relative h-10 w-10 flex items-center justify-center mx-auto rounded-lg transition-all duration-150 ease-out active:scale-[0.98] outline-none ${
            active
              ? 'bg-primary text-primary-foreground font-semibold shadow-xs ring-2 ring-primary/20'
              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
          }`}
        >
          <Icon className="h-5 w-5 shrink-0" strokeWidth={2} />
          {active && (
            <span className="absolute top-1 right-1 flex h-1.5 w-1.5 rounded-full bg-primary-foreground" />
          )}
        </NavLink>
      </TooltipTrigger>
      <TooltipContent side="right" sideOffset={12}>
        {section.label}
      </TooltipContent>
    </Tooltip>
  )
}

function CollapsedGroupItem({ section, active, pathname, onNavigate }) {
  const [open, setOpen] = useState(false)
  const timeoutRef = useRef(null)

  const handleMouseEnter = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    setOpen(true)
  }

  const handleMouseLeave = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    timeoutRef.current = setTimeout(() => {
      setOpen(false)
    }, 180)
  }

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [])

  const Icon = section.icon

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          onClick={() => setOpen((prev) => !prev)}
          aria-label={section.label}
          className={`relative h-10 w-10 flex items-center justify-center mx-auto rounded-lg transition-all duration-150 ease-out active:scale-[0.98] cursor-pointer outline-none ${
            active
              ? 'bg-primary text-primary-foreground font-semibold shadow-xs ring-2 ring-primary/20'
              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
          }`}
        >
          <Icon className="h-5 w-5 shrink-0" strokeWidth={2} />
          {active && (
            <span className="absolute top-1 right-1 flex h-1.5 w-1.5 rounded-full bg-primary-foreground" />
          )}
        </button>
      </PopoverTrigger>

      <PopoverContent
        side="right"
        align="start"
        sideOffset={14}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        className="w-56 p-2 rounded-xl shadow-xl border border-border bg-popover text-popover-foreground animate-in fade-in-0 zoom-in-95 z-50"
      >
        {/* Header with Title and Count */}
        <div className="flex items-center justify-between px-2 py-1.5 mb-1 border-b border-border/70">
          <div className="flex items-center gap-2 min-w-0">
            <Icon className="h-4 w-4 text-primary shrink-0" strokeWidth={2} />
            <span className="text-xs font-semibold text-foreground tracking-tight truncate">
              {section.label}
            </span>
          </div>
          <span className="text-[10px] font-semibold text-muted-foreground bg-muted px-1.5 py-0.5 rounded-full">
            {section.children.length}
          </span>
        </div>

        {/* Subtabs List */}
        <div className="flex flex-col space-y-1">
          {section.children.map((child) => {
            const isChildActive =
              pathname === child.to || pathname.startsWith(child.to + '/')
            return (
              <NavLink
                key={child.to}
                to={child.to}
                onClick={() => {
                  setOpen(false)
                  onNavigate?.()
                }}
                className={`w-full flex items-center justify-between px-2.5 py-1.5 text-xs rounded-md font-medium transition-all duration-150 active:scale-[0.98] ${
                  isChildActive
                    ? 'bg-primary text-primary-foreground font-semibold shadow-2xs'
                    : 'text-foreground hover:bg-accent'
                }`}
              >
                <span className="truncate">{child.label}</span>
                {isChildActive && (
                  <span className="h-1.5 w-1.5 rounded-full bg-primary-foreground shrink-0" />
                )}
              </NavLink>
            )
          })}
        </div>
      </PopoverContent>
    </Popover>
  )
}

export default function Sidebar({
  sections,
  portalLabel,
  collapsed = false,
  onNavigate,
}) {
  const location = useLocation()
  const [navState, setNavState] = useState({
    prevPath: location.pathname,
    openLabel: sections.find((s) => s.children && isSectionActive(s, location.pathname))?.label ?? null,
  })

  let openLabel = navState.openLabel
  if (navState.prevPath !== location.pathname) {
    const activeSection = sections.find((s) => s.children && isSectionActive(s, location.pathname))
    openLabel = activeSection?.label ?? null
    setNavState({
      prevPath: location.pathname,
      openLabel,
    })
  }

  const handleToggle = (label) => {
    setNavState((prev) => ({
      ...prev,
      openLabel: prev.openLabel === label ? null : label,
    }))
  }

  return (
    <aside className={`h-full flex flex-col justify-between ${collapsed ? 'p-2' : 'p-4'}`}>
      <div className="flex flex-col min-w-0">
        {/* Portal Header */}
        {!collapsed && portalLabel && (
          <div className="px-3 pb-3 mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground border-b border-border truncate">
            {portalLabel}
          </div>
        )}

        {/* Navigation list */}
        <nav className="flex flex-col space-y-1.5">
          {sections.map((section) => {
            const Icon = section.icon
            const active = isSectionActive(section, location.pathname)
            const hasChildren = Boolean(section.children && section.children.length > 0)

            // ---------------------------------------------------------------
            // 1. COLLAPSED MODE
            // ---------------------------------------------------------------
            if (collapsed) {
              if (!hasChildren) {
                return (
                  <CollapsedSimpleItem
                    key={section.label}
                    section={section}
                    active={active}
                    onNavigate={onNavigate}
                  />
                )
              }

              return (
                <CollapsedGroupItem
                  key={section.label}
                  section={section}
                  active={active}
                  pathname={location.pathname}
                  onNavigate={onNavigate}
                />
              )
            }

            // ---------------------------------------------------------------
            // 2. EXPANDED MODE: SIMPLE NAV LINK (NO CHILDREN)
            // ---------------------------------------------------------------
            if (!hasChildren) {
              return (
                <div key={section.label}>
                  <NavLink
                    to={section.to}
                    onClick={onNavigate}
                    className={`flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-all duration-150 ease-out active:scale-[0.98] ${
                      active
                        ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                    }`}
                  >
                    <Icon className="h-4 w-4 shrink-0" strokeWidth={2} />
                    <span className="truncate">{section.label}</span>
                  </NavLink>
                </div>
              )
            }

            // ---------------------------------------------------------------
            // 3. EXPANDED MODE: ACCORDION GROUP LINK (HAS CHILDREN)
            // ---------------------------------------------------------------
            const isOpen = openLabel === section.label
            return (
              <div key={section.label} className="space-y-1">
                <button
                  type="button"
                  className={`w-full flex items-center justify-between px-3 py-2 text-sm rounded-lg transition-all duration-150 ease-out active:scale-[0.98] cursor-pointer ${
                    active
                      ? 'bg-primary/10 text-primary font-semibold ring-1 ring-primary/15'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground font-medium'
                  }`}
                  onClick={() => handleToggle(section.label)}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Icon
                      className={`h-4 w-4 shrink-0 ${active ? 'text-primary' : ''}`}
                      strokeWidth={2}
                    />
                    <span className="truncate">{section.label}</span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {active && !isOpen && (
                      <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                    )}
                    <ChevronDown
                      className={`h-4 w-4 shrink-0 transition-transform duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] ${
                        isOpen ? 'rotate-180' : ''
                      }`}
                      strokeWidth={2}
                    />
                  </div>
                </button>
                {isOpen && (
                  <div className="ml-4 pl-3 border-l-2 border-primary/20 flex flex-col space-y-1 pt-1 animate-fade-rise">
                    {section.children.map((child) => {
                      const isChildActive =
                        location.pathname === child.to || location.pathname.startsWith(child.to + '/')
                      return (
                        <NavLink
                          key={child.to}
                          to={child.to}
                          onClick={onNavigate}
                          className={`flex items-center justify-between px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-150 ease-out active:scale-[0.98] ${
                            isChildActive
                              ? 'bg-primary text-primary-foreground font-semibold shadow-2xs'
                              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                          }`}
                        >
                          <span className="truncate">{child.label}</span>
                          {isChildActive && (
                            <span className="h-1.5 w-1.5 rounded-full bg-primary-foreground shrink-0" />
                          )}
                        </NavLink>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </nav>
      </div>
    </aside>
  )
}

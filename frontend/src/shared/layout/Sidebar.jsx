import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { ChevronDown } from 'lucide-react'

function isChildActive(section, pathname) {
  if (section.to) return pathname === section.to || pathname.startsWith(section.to + '/')
  return (section.children ?? []).some((c) => pathname.startsWith(c.to))
}

export default function Sidebar({ sections, portalLabel, onNavigate }) {
  const location = useLocation()
  const [openLabel, setOpenLabel] = useState(
    () => sections.find((s) => s.children && isChildActive(s, location.pathname))?.label ?? null,
  )

  return (
    <aside className="w-64 shrink-0 flex flex-col p-4">
      {portalLabel && (
        <div className="px-3 pb-3 mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground border-b border-border">
          {portalLabel}
        </div>
      )}
      <nav className="flex flex-col space-y-1">
        {sections.map((section) => {
          const Icon = section.icon
          const active = isChildActive(section, location.pathname)

          if (!section.children) {
            return (
              <NavLink
                key={section.label}
                to={section.to}
                end={section.to === '/student' || section.to === '/instructor' || section.to === '/admin'}
                onClick={onNavigate}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-all duration-150 ease-out active:scale-[0.98] ${
                    isActive
                      ? 'bg-primary text-primary-foreground shadow-xs'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  }`
                }
              >
                <Icon className="h-4 w-4 shrink-0" strokeWidth={2} />
                <span className="truncate">{section.label}</span>
              </NavLink>
            )
          }

          const isOpen = openLabel === section.label
          return (
            <div key={section.label} className="space-y-1">
              <button
                type="button"
                className={`w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-lg transition-all duration-150 ease-out active:scale-[0.98] cursor-pointer ${
                  active && !isOpen
                    ? 'bg-accent text-accent-foreground font-semibold'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                }`}
                onClick={() => setOpenLabel(isOpen ? null : section.label)}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Icon className="h-4 w-4 shrink-0" strokeWidth={2} />
                  <span className="truncate">{section.label}</span>
                </div>
                <ChevronDown
                  className={`h-4 w-4 shrink-0 transition-transform duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] ${isOpen ? 'rotate-180' : ''}`}
                  strokeWidth={2}
                />
              </button>
              {isOpen && (
                <div className="ml-4 pl-3 border-l border-border flex flex-col space-y-1 pt-1 animate-fade-rise">
                  {section.children.map((child) => (
                    <NavLink
                      key={child.to}
                      to={child.to}
                      onClick={onNavigate}
                      className={({ isActive }) =>
                        `flex items-center px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-150 ease-out active:scale-[0.98] ${
                          isActive
                            ? 'bg-primary/10 text-primary font-semibold'
                            : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                        }`
                      }
                    >
                      <span className="truncate">{child.label}</span>
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </nav>
    </aside>
  )
}


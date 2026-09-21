import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { ChevronDown } from 'lucide-react'
import './Sidebar.css'

function isChildActive(section, pathname) {
  if (section.to) return pathname === section.to || pathname.startsWith(section.to + '/')
  return (section.children ?? []).some((c) => pathname.startsWith(c.to))
}

export default function Sidebar({ sections, portalLabel }) {
  const location = useLocation()
  const [openLabel, setOpenLabel] = useState(
    () => sections.find((s) => s.children && isChildActive(s, location.pathname))?.label ?? null,
  )

  return (
    <aside className="sidebar">
      <p className="sidebar__portal-label">{portalLabel}</p>
      <nav className="sidebar__nav">
        {sections.map((section) => {
          const Icon = section.icon
          const active = isChildActive(section, location.pathname)

          if (!section.children) {
            return (
              <NavLink
                key={section.label}
                to={section.to}
                end={section.to === '/student' || section.to === '/instructor' || section.to === '/admin'}
                className={({ isActive }) =>
                  'sidebar__item' + (isActive ? ' sidebar__item--active' : '')
                }
                style={{ '--group-color': section.color ?? 'var(--color-primary)' }}
              >
                <Icon size={18} strokeWidth={2} />
                <span>{section.label}</span>
              </NavLink>
            )
          }

          const isOpen = openLabel === section.label
          return (
            <div key={section.label} className="sidebar__group">
              <button
                type="button"
                className={'sidebar__item sidebar__item--toggle' + (active ? ' sidebar__item--active' : '')}
                style={{ '--group-color': section.color ?? 'var(--color-primary)' }}
                onClick={() => setOpenLabel(isOpen ? null : section.label)}
              >
                <Icon size={18} strokeWidth={2} />
                <span>{section.label}</span>
                <ChevronDown
                  size={15}
                  strokeWidth={2}
                  className={'sidebar__chevron' + (isOpen ? ' sidebar__chevron--open' : '')}
                />
              </button>
              {isOpen && (
                <div className="sidebar__submenu">
                  {section.children.map((child) => (
                    <NavLink
                      key={child.to}
                      to={child.to}
                      className={({ isActive }) =>
                        'sidebar__subitem' + (isActive ? ' sidebar__subitem--active' : '')
                      }
                      style={{ '--group-color': section.color ?? 'var(--color-primary)' }}
                    >
                      {child.label}
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

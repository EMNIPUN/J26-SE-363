import { NavLink } from 'react-router-dom'
import { MODULES } from '../constants/modules'
import './TopNav.css'

export default function TopNav() {
  return (
    <header className="top-nav">
      <NavLink to="/" end className="top-nav__brand">
        J26-SE-363
      </NavLink>
      <nav className="top-nav__links">
        {MODULES.map((m) => (
          <NavLink
            key={m.key}
            to={m.path}
            className={({ isActive }) =>
              'top-nav__link' + (isActive ? ' top-nav__link--active' : '')
            }
            style={{ '--module-color': m.color }}
          >
            {m.label}
          </NavLink>
        ))}
      </nav>
    </header>
  )
}

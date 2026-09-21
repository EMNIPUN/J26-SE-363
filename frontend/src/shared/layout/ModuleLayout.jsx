import { NavLink, Outlet, Link } from 'react-router-dom'
import './ModuleLayout.css'

/**
 * Shared chrome for every module: a colored banner + a side nav built from
 * that module's own `navLinks`. Each module's routes.jsx supplies its
 * metadata (from shared/constants/modules.js) and its own link list, so this
 * component never needs to know which module it's rendering.
 */
export default function ModuleLayout({ module, navLinks }) {
  return (
    <div className="module-layout" style={{ '--module-color': module.color }}>
      <div className="module-layout__banner">
        <Link to="/" className="module-layout__home">
          ← All components
        </Link>
        <h2 className="module-layout__title">{module.label}</h2>
        <p className="module-layout__owner">{module.owner}</p>
      </div>
      <div className="module-layout__body">
        <nav className="module-layout__nav">
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                'module-layout__nav-link' + (isActive ? ' module-layout__nav-link--active' : '')
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="module-layout__content">
          <Outlet />
        </div>
      </div>
    </div>
  )
}

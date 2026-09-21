import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'
import Card from './Card.jsx'
import './ComponentLinkGrid.css'

/**
 * Grid of "jump into a component" cards, used on every role's dashboard
 * home. `items` is a filtered slice of MODULES (each role only sees the
 * components relevant to it) with an explicit `to` (that role's entry page).
 */
export default function ComponentLinkGrid({ items }) {
  return (
    <div className="component-grid">
      {items.map((m) => (
        <Card key={m.key} className="component-grid__card" style={{ '--module-color': m.color }}>
          <Link to={m.to} className="component-grid__link">
            <span className="component-grid__owner">{m.owner}</span>
            <h3 className="component-grid__title">{m.label}</h3>
            <p className="component-grid__tagline">{m.tagline}</p>
            <span className="component-grid__cta">
              Open <ArrowUpRight size={14} strokeWidth={2.2} />
            </span>
          </Link>
        </Card>
      ))}
    </div>
  )
}

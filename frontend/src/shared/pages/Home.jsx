import { Link } from 'react-router-dom'
import { MODULES } from '../constants/modules'
import './Home.css'

export default function Home() {
  return (
    <div className="home">
      <h1 className="home__title">J26-SE-363</h1>
      <p className="home__subtitle">
        Pick a component below. Each one owns its own routes, pages and folder — this
        page just links across them.
      </p>
      <div className="home__grid">
        {MODULES.map((m) => (
          <Link key={m.key} to={m.path} className="home__card" style={{ '--module-color': m.color }}>
            <span className="home__card-owner">{m.owner}</span>
            <h2 className="home__card-title">{m.label}</h2>
            <p className="home__card-tagline">{m.tagline}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}

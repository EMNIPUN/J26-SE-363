import { getModule } from '../constants/modules'
import PageHeader from './PageHeader.jsx'
import Card from './Card.jsx'
import './PlaceholderPage.css'

/**
 * Generic dummy-content page. Every real page in a module starts as a thin
 * wrapper around this until the actual feature is implemented, so the
 * routing/navigation and shared theme can be demoed before any real UI
 * exists for that page.
 */
export default function PlaceholderPage({
  moduleKey,
  title,
  breadcrumb = [],
  description,
  bullets = [],
}) {
  const module = getModule(moduleKey)

  return (
    <div style={{ '--module-color': module?.color }}>
      <PageHeader title={title} breadcrumb={breadcrumb} description={description} />

      {bullets.length > 0 && (
        <Card className="placeholder-page__card">
          <p className="placeholder-page__card-label">Planned for this page</p>
          <ul className="placeholder-page__bullets">
            {bullets.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Card>
      )}

      <div className="placeholder-page__stub">Dummy content — real UI for this page is not implemented yet.</div>
    </div>
  )
}

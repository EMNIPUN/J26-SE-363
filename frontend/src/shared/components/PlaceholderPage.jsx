import { getModule } from '../constants/modules'
import './PlaceholderPage.css'

/**
 * Generic dummy-content page. Every real page in a module starts as a thin
 * wrapper around this until the actual feature is implemented, so the
 * routing/navigation can be demoed before any real UI exists.
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
    <article className="placeholder-page" style={{ '--module-color': module?.color }}>
      {breadcrumb.length > 0 && (
        <p className="placeholder-page__breadcrumb">{breadcrumb.join(' / ')}</p>
      )}
      <h1 className="placeholder-page__title">{title}</h1>
      {description && <p className="placeholder-page__description">{description}</p>}
      {bullets.length > 0 && (
        <ul className="placeholder-page__bullets">
          {bullets.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
      <div className="placeholder-page__stub">
        Dummy content — real UI for this page is not implemented yet.
      </div>
    </article>
  )
}

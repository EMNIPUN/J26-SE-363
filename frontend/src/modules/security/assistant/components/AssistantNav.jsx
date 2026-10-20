import { Link, useLocation, useParams } from 'react-router-dom'

const PAGES = [
  { to: '', label: 'Overview' },
  { to: '/findings', label: 'Findings by type' },
  { to: '/learning', label: 'Comprehension checks (mock)' },
  { to: '/agents', label: 'Agents and governance' },
]

// Page links of the Security Assistant section; the chosen run and student stay in the address (?run=...&student=...).
export default function AssistantNav() {
  const { teamId } = useParams()
  const { pathname, search } = useLocation()
  const base = `/teams/${teamId}/security/assistant`
  return (
    <nav aria-label="Security Assistant pages" className="flex flex-wrap gap-1 border-b border-border">
      {PAGES.map((page) => {
        const href = `${base}${page.to}`
        const active = page.to === '' ? pathname === base || pathname === `${base}/` : pathname.startsWith(href)
        return (
          <Link
            key={page.label}
            to={`${href}${search}`}
            aria-current={active ? 'page' : undefined}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${active ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
          >
            {page.label}
          </Link>
        )
      })}
    </nav>
  )
}

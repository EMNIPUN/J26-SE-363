import { FlaskConical, Info, TriangleAlert } from 'lucide-react'
import Badge from '@/shared/components/Badge.jsx'
import { DEMO_NOTE } from '../config.js'

// Used next to every score, question result and summary the mock Tutor produced.
export function MockBadge({ children = 'MOCK', className = '' }) {
  return (
    <Badge tone="warning" className={className} title="The Tutor is a mock: no student was asked and no answer was graded.">
      <FlaskConical className="h-3 w-3" />
      {children}
    </Badge>
  )
}

// One sentence at the top of every page: what you are looking at and how to read it.
export function HowToRead({ children }) {
  return (
    <p data-slot="how-to-read" className="flex items-start gap-2 rounded-lg border border-border/70 bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>
        <span className="font-semibold text-foreground">How to read this page. </span>
        {children}
      </span>
    </p>
  )
}

// Shown whenever the data comes from the checked-in sample (the server flag or the browser flag), never otherwise.
export function DemoBanner({ active }) {
  if (!active) return null
  return (
    <div role="status" data-slot="demo-banner" className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
      <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>
        <span className="font-semibold">DEMO DATA. </span>
        {DEMO_NOTE}
      </span>
    </div>
  )
}

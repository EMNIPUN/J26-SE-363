import { FlaskConical } from 'lucide-react'
import { SAMPLE_NOTICE } from '../data/tutorWorkspace.js'

export default function SampleBanner() {
  return (
    <div className="flex gap-3 rounded-xl border border-border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
      <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
      <p>{SAMPLE_NOTICE}</p>
    </div>
  )
}

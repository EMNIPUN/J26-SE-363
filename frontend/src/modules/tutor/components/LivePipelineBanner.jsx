import { Activity } from 'lucide-react'

export default function LivePipelineBanner({ mode = 'live' }) {
  const text =
    mode === 'live'
      ? 'Live Adaptive Tutor pipeline (PP1): sprint context → required knowledge → MCP evidence → BKT mastery. Adaptive decisions are not generated yet.'
      : 'Sample / upcoming tutor surface. Not part of the PP1 live demonstration path.'

  return (
    <div className="flex gap-3 rounded-xl border border-border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
      <Activity className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
      <p>{text}</p>
    </div>
  )
}

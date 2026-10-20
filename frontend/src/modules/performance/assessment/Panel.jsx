import PropTypes from 'prop-types'
import { Info } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

/** A small "i" that opens the longer explanation of a part of the page, so the page itself can stay short. */
export function InfoTip({ label, children }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button type="button" aria-label={`About: ${label}`} className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
          <Info className="h-4 w-4" aria-hidden="true" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-80 rounded-xl p-4 text-sm leading-relaxed text-muted-foreground shadow-xl">{children}</PopoverContent>
    </Popover>
  )
}
InfoTip.propTypes = { label: PropTypes.string, children: PropTypes.node }

/**
 * One clearly separated part of a page: its own box, a header with an icon, a short title and subtitle, then the content.
 * Anything longer than a line goes in `info`, behind the "i", so the box stays easy to scan.
 */
export default function Panel({ title, hint, info, icon: Icon, aside, tone = 'default', id, children }) {
  const chip = tone === 'warning' ? 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300' : 'bg-primary/10 text-primary'
  return (
    <section id={id} className="scroll-mt-16 overflow-hidden rounded-2xl border bg-card shadow-sm">
      <header className="flex flex-wrap items-center gap-3 border-b bg-muted/40 px-5 py-3.5 @xl:px-6">
        {Icon && <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${chip}`}><Icon className="h-4.5 w-4.5" aria-hidden="true" /></span>}
        <div className="min-w-0 flex-1">
          <h3 className="flex items-center gap-1.5 text-base font-semibold tracking-tight text-foreground">{title}{info && <InfoTip label={title}>{info}</InfoTip>}</h3>
          {hint && <p className="truncate text-sm text-muted-foreground">{hint}</p>}
        </div>
        {aside}
      </header>
      <div className="p-5 @xl:p-6">{children}</div>
    </section>
  )
}
Panel.propTypes = { title: PropTypes.string, hint: PropTypes.string, info: PropTypes.node, icon: PropTypes.elementType, aside: PropTypes.node, tone: PropTypes.string, id: PropTypes.string, children: PropTypes.node }

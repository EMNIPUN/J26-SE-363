import PropTypes from 'prop-types'

/** One clearly separated part of a page: its own box, a header with an icon, a title and what it is for, then the content. */
export default function Panel({ title, hint, icon: Icon, aside, tone = 'default', children }) {
  const chip = tone === 'warning' ? 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300' : 'bg-primary/10 text-primary'
  return (
    <section className="overflow-hidden rounded-2xl border bg-card shadow-sm">
      <header className="flex flex-wrap items-start gap-3 border-b bg-muted/40 px-5 py-4 sm:px-6">
        {Icon && <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${chip}`}><Icon className="h-[18px] w-[18px]" aria-hidden="true" /></span>}
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-semibold tracking-tight text-foreground">{title}</h3>
          {hint && <p className="mt-0.5 text-sm leading-relaxed text-muted-foreground">{hint}</p>}
        </div>
        {aside}
      </header>
      <div className="p-5 sm:p-6">{children}</div>
    </section>
  )
}
Panel.propTypes = { title: PropTypes.string, hint: PropTypes.string, icon: PropTypes.elementType, aside: PropTypes.node, tone: PropTypes.string, children: PropTypes.node }

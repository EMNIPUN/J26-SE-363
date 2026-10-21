import { Children, useEffect, useRef, useState } from 'react'
import PropTypes from 'prop-types'

/** One shimmering block: the building piece of every skeleton. */
export function Skel({ className = '', style }) {
  return <span className={`block animate-pulse rounded-md bg-muted ${className}`} style={style} aria-hidden="true" />
}
Skel.propTypes = { className: PropTypes.string, style: PropTypes.object }

/** A panel-shaped placeholder: the header with its icon and title, then a few lines. */
export function PanelSkeleton({ height = 180, title = true }) {
  return (
    <div className="overflow-hidden rounded-2xl border bg-card shadow-sm" style={{ minHeight: height }} aria-busy="true" aria-live="polite">
      {title && (
        <div className="flex items-center gap-3 border-b bg-muted/40 px-6 py-4">
          <Skel className="h-9 w-9 rounded-xl" />
          <div className="space-y-2"><Skel className="h-3.5 w-40" /><Skel className="h-2.5 w-64 bg-muted/70" /></div>
        </div>
      )}
      <div className="space-y-3 p-6">
        <Skel className="h-3 w-11/12" />
        <Skel className="h-3 w-9/12 [animation-delay:120ms]" />
        <Skel className="h-3 w-10/12 [animation-delay:240ms]" />
      </div>
    </div>
  )
}
PanelSkeleton.propTypes = { height: PropTypes.number, title: PropTypes.bool }

/** The row of number cards at the top of a tab. */
export function StatRowSkeleton({ count = 4 }) {
  return (
    <div className="grid gap-4 @xl:grid-cols-2 @5xl:grid-cols-4" aria-busy="true">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="flex items-center gap-4 rounded-xl border bg-card p-4 shadow-sm">
          <Skel className="h-11 w-11 rounded-xl" style={{ animationDelay: `${i * 90}ms` }} />
          <div className="min-w-0 flex-1 space-y-2"><Skel className="h-2.5 w-20" /><Skel className="h-6 w-16" /><Skel className="h-2.5 w-28 bg-muted/70" /></div>
        </div>
      ))}
    </div>
  )
}
StatRowSkeleton.propTypes = { count: PropTypes.number }

/** A table: a header line and rows with a round photo, some text and a few cells. */
export function TableSkeleton({ rows = 4, columns = 5 }) {
  return (
    <div className="overflow-hidden rounded-2xl border bg-card shadow-sm" aria-busy="true">
      <div className="flex gap-6 border-b bg-muted/40 px-5 py-3">{Array.from({ length: columns }, (_, i) => <Skel key={i} className={`h-3 ${i === 0 ? 'w-28' : 'w-16'}`} />)}</div>
      {Array.from({ length: rows }, (_, r) => (
        <div key={r} className="flex items-center gap-6 border-b px-5 py-4 last:border-b-0">
          <div className="flex w-40 items-center gap-3"><Skel className="h-9 w-9 rounded-full" style={{ animationDelay: `${r * 100}ms` }} /><Skel className="h-3 w-24" /></div>
          {Array.from({ length: columns - 1 }, (_, c) => <Skel key={c} className="h-3 w-16" style={{ animationDelay: `${(r + c) * 60}ms` }} />)}
        </div>
      ))}
    </div>
  )
}
TableSkeleton.propTypes = { rows: PropTypes.number, columns: PropTypes.number }

/** A list of cards, each a line of text with a pill and a button. */
export function ListSkeleton({ rows = 4 }) {
  return (
    <div className="space-y-3" aria-busy="true">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-4 rounded-xl border bg-card p-4 shadow-sm">
          <Skel className="h-6 w-20 rounded-full" style={{ animationDelay: `${i * 90}ms` }} />
          <div className="flex-1 space-y-2"><Skel className="h-3.5 w-56" /><Skel className="h-2.5 w-40 bg-muted/70" /></div>
          <Skel className="h-8 w-28 rounded-md" />
        </div>
      ))}
    </div>
  )
}
ListSkeleton.propTypes = { rows: PropTypes.number }

/** A chart panel: its header and a grid of bars. */
export function ChartSkeleton({ height = 260 }) {
  const bars = [46, 70, 38, 82, 58, 90, 64]
  return (
    <div className="overflow-hidden rounded-2xl border bg-card shadow-sm" aria-busy="true">
      <div className="flex items-center gap-3 border-b bg-muted/40 px-6 py-4"><Skel className="h-9 w-9 rounded-xl" /><div className="space-y-2"><Skel className="h-3.5 w-44" /><Skel className="h-2.5 w-72 bg-muted/70" /></div></div>
      <div className="flex items-end gap-3 p-6" style={{ height }}>{bars.map((h, i) => <Skel key={i} className="flex-1 rounded-t-md" style={{ height: `${h}%`, animationDelay: `${i * 80}ms` }} />)}</div>
    </div>
  )
}
ChartSkeleton.propTypes = { height: PropTypes.number }

/** The profile header of a student: banner, photo, name and chips. */
export function ProfileSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl border bg-card shadow-sm" aria-busy="true">
      <Skel className="h-28 w-full rounded-none @xl:h-32" />
      <div className="flex flex-col gap-5 px-6 pb-6 @xl:flex-row @xl:items-end @xl:gap-6">
        <Skel className="-mt-14 h-28 w-28 shrink-0 rounded-full border-4 border-card @xl:-mt-16" />
        <div className="flex-1 space-y-3 @xl:pb-1"><Skel className="h-9 w-72 max-w-full" /><div className="flex gap-2"><Skel className="h-6 w-28 rounded-full" /><Skel className="h-6 w-36 rounded-full" /><Skel className="h-6 w-24 rounded-full" /></div></div>
        <Skel className="h-[74px] w-28 rounded-2xl @xl:mb-1" />
      </div>
    </div>
  )
}

/** The vertical pipeline of a run: a line of steps, and the log beside it. */
export function PipelineSkeleton() {
  return (
    <div className="grid gap-5 @5xl:grid-cols-[minmax(0,1fr)_380px]" aria-busy="true">
      <div className="max-w-3xl space-y-4">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="flex gap-3">
            <Skel className="h-8 w-8 shrink-0 rounded-full" style={{ animationDelay: `${i * 90}ms` }} />
            <div className="flex-1 space-y-2 rounded-xl border bg-card p-4 shadow-sm"><Skel className="h-3.5 w-40" /><Skel className="h-2.5 w-24 bg-muted/70" /><Skel className="h-2.5 w-52 bg-muted/70" /></div>
          </div>
        ))}
      </div>
      <div className="space-y-4"><PanelSkeleton height={90} title={false} /><PanelSkeleton height={260} /></div>
    </div>
  )
}

/**
 * Brings the children in one after another instead of all at once: each fades up a little after the one before it.
 * Meant for a screen that has just got its data; the children are already there, only their arrival is staggered.
 */
export function Stagger({ children, step = 90, start = 0, className = '' }) {
  return (
    <div className={className}>
      {Children.toArray(children).filter(Boolean).map((child, i) => <div key={child.key ?? i} className="animate-fade-rise" style={{ animationDelay: `${start + i * step}ms` }}>{child}</div>)}
    </div>
  )
}
Stagger.propTypes = { children: PropTypes.node, step: PropTypes.number, start: PropTypes.number, className: PropTypes.string }

/**
 * Brings a part of the page in step by step instead of all at once: it shows a placeholder, waits `delay` ms, then fades up.
 * With `lazy` it waits until the part is about to scroll into view, and tells the page with `onSeen(name)` so the data behind it is only asked for then.
 */
export default function Reveal({ children, delay = 0, lazy = false, compact = false, height = 180, id, name, onSeen, skeleton }) {
  const box = useRef(null)
  const [state, setState] = useState(lazy ? 'hidden' : 'waiting')

  useEffect(() => {
    if (state !== 'hidden') return undefined
    const el = box.current
    if (!el || typeof IntersectionObserver === 'undefined') { setState('waiting'); return undefined }
    const watcher = new IntersectionObserver((entries) => { if (entries.some((e) => e.isIntersecting)) { setState('waiting'); watcher.disconnect() } }, { rootMargin: '280px 0px' })
    watcher.observe(el)
    return () => watcher.disconnect()
  }, [state])

  useEffect(() => {
    if (state !== 'waiting') return undefined
    onSeen?.(name)
    const t = setTimeout(() => setState('shown'), delay)
    return () => clearTimeout(t)
  }, [state, delay, name, onSeen])

  if (state === 'shown') return <div id={id} className="scroll-mt-16 animate-fade-rise">{children}</div>
  return <div id={id} ref={box} className="scroll-mt-16">{skeleton || <PanelSkeleton height={height} title={!compact} />}</div>
}
Reveal.propTypes = { children: PropTypes.node, delay: PropTypes.number, lazy: PropTypes.bool, compact: PropTypes.bool, height: PropTypes.number, id: PropTypes.string, name: PropTypes.string, onSeen: PropTypes.func, skeleton: PropTypes.node }

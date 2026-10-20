import { useEffect, useRef, useState } from 'react'
import PropTypes from 'prop-types'

/** A panel-shaped placeholder that pulses while the real thing is not there yet. */
export function PanelSkeleton({ height = 180, title = true }) {
  return (
    <div className="overflow-hidden rounded-2xl border bg-card shadow-sm" style={{ minHeight: height }} aria-busy="true" aria-live="polite">
      {title && (
        <div className="flex items-center gap-3 border-b bg-muted/40 px-6 py-4">
          <span className="h-9 w-9 animate-pulse rounded-xl bg-muted" />
          <div className="space-y-2"><span className="block h-3.5 w-40 animate-pulse rounded bg-muted" /><span className="block h-2.5 w-64 animate-pulse rounded bg-muted/70" /></div>
        </div>
      )}
      <div className="space-y-3 p-6">
        <span className="block h-3 w-11/12 animate-pulse rounded bg-muted" />
        <span className="block h-3 w-9/12 animate-pulse rounded bg-muted [animation-delay:120ms]" />
        <span className="block h-3 w-10/12 animate-pulse rounded bg-muted [animation-delay:240ms]" />
      </div>
    </div>
  )
}
PanelSkeleton.propTypes = { height: PropTypes.number, title: PropTypes.bool }

/**
 * Brings a part of the page in step by step instead of all at once: it shows a placeholder, waits `delay` ms, then fades up.
 * With `lazy` it waits until the part is about to scroll into view, and tells the page with `onSeen(name)` so the data behind it is only asked for then.
 */
export default function Reveal({ children, delay = 0, lazy = false, compact = false, height = 180, name, onSeen }) {
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

  if (state === 'shown') return <div className="animate-fade-rise">{children}</div>
  return <div ref={box}><PanelSkeleton height={height} title={!compact} /></div>
}
Reveal.propTypes = { children: PropTypes.node, delay: PropTypes.number, lazy: PropTypes.bool, compact: PropTypes.bool, height: PropTypes.number, name: PropTypes.string, onSeen: PropTypes.func }

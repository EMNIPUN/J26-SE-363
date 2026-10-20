import { useLayoutEffect, useState } from 'react'

/** The frame whose width the page really has: the team workspace, which gets narrower when the AI chat opens beside it. */
export const frameOf = (el) => el?.closest('.workspace-container, main') || el?.parentElement || null

/** The element that scrolls the page the element is on (the team workspace), or null when the window itself scrolls. */
export function scrollerOf(el) {
  for (let p = el?.parentElement; p; p = p.parentElement) {
    const y = getComputedStyle(p).overflowY
    if (y === 'auto' || y === 'scroll') return p
  }
  return null
}

/**
 * The width of the space an element lives in, kept up to date. The window is the wrong thing to ask: the AI chat takes a third of it, and the page must follow the space it has left.
 * Returns 0 until it has been measured.
 */
export function useContainerWidth(ref) {
  const [width, setWidth] = useState(0)
  useLayoutEffect(() => {
    const frame = frameOf(ref.current)
    if (!frame) return undefined
    const measure = () => setWidth(frame.clientWidth)
    measure()
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', measure)
      return () => window.removeEventListener('resize', measure)
    }
    const watcher = new ResizeObserver(measure)
    watcher.observe(frame)
    return () => watcher.disconnect()
  }, [ref])
  return width
}

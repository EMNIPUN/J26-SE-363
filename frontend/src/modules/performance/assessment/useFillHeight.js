import { useLayoutEffect, useState } from 'react'
import { frameOf } from './useContainerWidth.js'

/**
 * The height that makes an element end exactly at the bottom of the window, so a page can be one fixed screen whose parts scroll on their own.
 * Returns null when the space the page has is narrow (it then flows and scrolls normally). "Narrow" is the width of the workspace, not of the window,
 * so it also holds when the AI chat is open beside it. Measured again when either changes size.
 */
export function useFillHeight(ref, minWidth = 1024) {
  const [height, setHeight] = useState(null)
  useLayoutEffect(() => {
    const el = ref.current
    const frame = frameOf(el)
    const measure = () => {
      if (!el) return
      if ((frame?.clientWidth ?? window.innerWidth) < minWidth) { setHeight(null); return }
      const below = frame ? parseFloat(getComputedStyle(frame).paddingBottom) || 0 : 0
      setHeight(Math.max(420, Math.floor(window.innerHeight - el.getBoundingClientRect().top - below - 2)))
    }
    measure()
    window.addEventListener('resize', measure)
    const watcher = typeof ResizeObserver === 'undefined' || !frame ? null : new ResizeObserver(measure)
    watcher?.observe(frame)
    return () => { window.removeEventListener('resize', measure); watcher?.disconnect() }
  }, [ref, minWidth])
  return height
}

import { useLayoutEffect, useState } from 'react'

/**
 * The height that makes an element end exactly at the bottom of the window, so a page can be one fixed screen whose parts scroll on their own.
 * Returns null on narrow screens (the page then flows and scrolls normally). Measured again when the window changes size.
 */
export function useFillHeight(ref, minWidth = 1280) {
  const [height, setHeight] = useState(null)
  useLayoutEffect(() => {
    const measure = () => {
      const el = ref.current
      if (!el || window.innerWidth < minWidth) { setHeight(null); return }
      const frame = el.closest('main')
      const below = frame ? parseFloat(getComputedStyle(frame).paddingBottom) || 0 : 0
      setHeight(Math.max(420, Math.floor(window.innerHeight - el.getBoundingClientRect().top - below - 2)))
    }
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [ref, minWidth])
  return height
}

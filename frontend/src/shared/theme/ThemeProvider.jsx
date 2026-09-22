import { useEffect, useState } from 'react'
import { ThemeContext } from './context.js'

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'mentor-theme',
}) {
  const [theme, setTheme] = useState(
    () =>
      localStorage.getItem(storageKey) ||
      localStorage.getItem('eduflow-theme') ||
      defaultTheme,
  )
  const [resolvedTheme, setResolvedTheme] = useState('light')

  useEffect(() => {
    const root = window.document.documentElement

    function applyTheme() {
      root.classList.remove('light', 'dark')

      let effectiveTheme = theme
      if (theme === 'system') {
        const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
        effectiveTheme = systemDark ? 'dark' : 'light'
      }

      root.classList.add(effectiveTheme)
      setResolvedTheme(effectiveTheme)
    }

    applyTheme()

    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      const listener = () => applyTheme()
      mediaQuery.addEventListener('change', listener)
      return () => mediaQuery.removeEventListener('change', listener)
    }
  }, [theme])

  const value = {
    theme,
    resolvedTheme,
    setTheme: (newTheme) => {
      localStorage.setItem(storageKey, newTheme)
      setTheme(newTheme)
    },
  }

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}


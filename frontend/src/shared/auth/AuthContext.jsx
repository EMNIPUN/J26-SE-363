import { useState, useCallback } from 'react'
import { AuthContext } from './context.js'

const STORAGE_KEY = 'j26_auth_user'

function readStoredUser() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(readStoredUser)

  const login = useCallback((account) => {
    const sessionUser = { name: account.name, email: account.email, role: account.role }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessionUser))
    } catch {
      // ignore write failures (private browsing, storage disabled, ...)
    }
    setUser(sessionUser)
  }, [])

  const logout = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch {
      // ignore
    }
    setUser(null)
  }, [])

  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>
}

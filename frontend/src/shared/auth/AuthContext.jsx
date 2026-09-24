import { useState, useEffect, useCallback, useMemo } from 'react'
import PropTypes from 'prop-types'
import { AuthContext } from './context.js'
import keycloak, { initKeycloak } from './keycloak.js'
import tokenManager from '../api/tokenManager.js'

const STORAGE_KEY = 'j26_auth_user'

function readStoredUser() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function resolveRole(roles = []) {
  if (roles.includes('admin')) return 'admin'
  if (roles.includes('lecturer') || roles.includes('instructor')) return 'instructor'
  return 'student'
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(readStoredUser)
  const [isInitialized, setIsInitialized] = useState(false)
  const [isKeycloak, setIsKeycloak] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  // Initialize Keycloak SSO on application startup
  useEffect(() => {
    let isMounted = true

    initKeycloak()
      .then((authenticated) => {
        if (!isMounted) return

        if (authenticated && keycloak.token) {
          tokenManager.setToken(keycloak.token)

          const parsed = keycloak.tokenParsed || {}
          const userRoles = parsed.realm_access?.roles || []
          const role = resolveRole(userRoles)

          const authUser = {
            name: parsed.name || parsed.preferred_username || 'User',
            email: parsed.email || '',
            username: parsed.preferred_username || '',
            role,
            roles: userRoles,
            isKeycloak: true,
          }

          try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(authUser))
          } catch {
            // ignore storage errors
          }

          setUser(authUser)
          setIsKeycloak(true)
        } else {
          // If Keycloak SSO is not active, clear any stale Keycloak session from localStorage
          const stored = readStoredUser()
          if (stored && stored.isKeycloak) {
            try {
              localStorage.removeItem(STORAGE_KEY)
            } catch {
              // ignore
            }
            setUser(null)
          }
        }
        setIsInitialized(true)
      })
      .catch((err) => {
        console.warn('Keycloak initialization error (gateway or service may be offline):', err)
        if (isMounted) {
          setIsInitialized(true)
        }
      })

    // Setup silent token refresh handler
    keycloak.onTokenExpired = () => {
      keycloak
        .updateToken(30)
        .then((refreshed) => {
          if (refreshed && keycloak.token) {
            tokenManager.setToken(keycloak.token)
          }
        })
        .catch(() => {
          tokenManager.clearToken()
        })
    }

    return () => {
      isMounted = false
    }
  }, [])

  // Explicit Keycloak OpenID Connect Login (via Kong Gateway)
  const loginWithKeycloak = useCallback(() => {
    return keycloak.login({
      redirectUri: `${window.location.origin}/`,
    })
  }, [])

  // Prototype Demo Account Login (in-memory & local fallback)
  const login = useCallback((account) => {
    const sessionUser = {
      name: account.name,
      email: account.email,
      role: account.role,
      roles: [account.role],
      isDemo: true,
    }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessionUser))
    } catch {
      // ignore storage errors
    }
    setUser(sessionUser)
    setIsKeycloak(false)
  }, [])

  // Unified Logout
  const logout = useCallback(() => {
    setIsLoggingOut(true)
    tokenManager.clearToken()
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch {
      // ignore
    }
    setUser(null)

    if (isKeycloak && keycloak.authenticated) {
      keycloak.logout({
        redirectUri: `${window.location.origin}/`,
        idTokenHint: keycloak.idToken,
      })
    } else {
      setIsLoggingOut(false)
    }
  }, [isKeycloak])

  const contextValue = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isInitialized,
      isKeycloak,
      isLoggingOut,
      token: keycloak.token || tokenManager.getToken(),
      login,
      loginWithKeycloak,
      logout,
    }),
    [user, isInitialized, isKeycloak, isLoggingOut, login, loginWithKeycloak, logout]
  )

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
}

AuthProvider.propTypes = {
  children: PropTypes.node.isRequired,
}

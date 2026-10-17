import { useState, useEffect, useCallback, useMemo } from 'react'
import PropTypes from 'prop-types'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AuthContext } from './context.js'
import keycloak, { initKeycloak } from './keycloak.js'
import tokenManager from '../api/tokenManager.js'
import { accountService, accountKeys } from '../services/accountService.js'

// Older builds kept the signed-in user, role included, in localStorage. A browser is no place to
// remember who someone is or what they may do, so that entry is removed.
const LEGACY_STORAGE_KEY = 'j26_auth_user'

// The Core API calls the role "lecturer"; the routes, guards and navigation call it "instructor".
const UI_ROLE = { student: 'student', lecturer: 'instructor', admin: 'admin' }

/**
 * Who is signed in.
 *
 * Keycloak proves who the person is (name, email). What they are in SELVIA (student, lecturer
 * or admin) and whether they finished onboarding comes from the Core API account, so `user.role`
 * is null until the person has completed onboarding.
 */
export function AuthProvider({ children }) {
  const queryClient = useQueryClient()
  const [identity, setIdentity] = useState(null)
  const [isKeycloakReady, setIsKeycloakReady] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  useEffect(() => {
    let isMounted = true

    try {
      localStorage.removeItem(LEGACY_STORAGE_KEY)
    } catch {
      // storage can be unavailable; nothing to clean up then
    }

    initKeycloak()
      .then((authenticated) => {
        if (!isMounted) return
        if (authenticated && keycloak.token) {
          tokenManager.setToken(keycloak.token)
          const parsed = keycloak.tokenParsed || {}
          setIdentity({
            name: parsed.name || parsed.preferred_username || '',
            email: parsed.email || '',
            username: parsed.preferred_username || '',
            isKeycloak: true,
          })
        }
        setIsKeycloakReady(true)
      })
      .catch((err) => {
        console.warn('Keycloak initialization error (gateway or service may be offline):', err)
        if (isMounted) setIsKeycloakReady(true)
      })

    // Silent token refresh
    keycloak.onTokenExpired = () => {
      keycloak
        .updateToken(30)
        .then((refreshed) => {
          if (refreshed && keycloak.token) tokenManager.setToken(keycloak.token)
        })
        .catch(() => tokenManager.clearToken())
    }

    return () => {
      isMounted = false
    }
  }, [])

  const accountQuery = useQuery({
    queryKey: accountKeys.me,
    queryFn: accountService.getMe,
    enabled: Boolean(identity),
    retry: 1,
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000,
  })
  const account = accountQuery.data ?? null

  // Ready once Keycloak has answered and, for a signed-in person, the account has loaded or failed.
  const isInitialized = isKeycloakReady && (!identity || !accountQuery.isPending)

  const user = useMemo(() => {
    if (!identity) return null
    return {
      ...identity,
      name: account?.name || identity.name,
      email: account?.email || identity.email,
      role: account?.role ? UI_ROLE[account.role] : null,
      onboarded: Boolean(account?.onboarding_completed),
    }
  }, [identity, account])

  const setAccount = useCallback(
    (next) => queryClient.setQueryData(accountKeys.me, next),
    [queryClient],
  )
  const refreshAccount = useCallback(
    () => queryClient.invalidateQueries({ queryKey: accountKeys.me }),
    [queryClient],
  )

  const loginWithKeycloak = useCallback(
    () => keycloak.login({ redirectUri: `${window.location.origin}/` }),
    [],
  )

  const logout = useCallback(() => {
    setIsLoggingOut(true)
    tokenManager.clearToken()
    queryClient.clear() // nothing from this person should survive in the cache
    if (keycloak.authenticated || keycloak.token) {
      keycloak.logout({ redirectUri: `${window.location.origin}/`, logoutMethod: 'GET' })
    } else {
      setIdentity(null)
      setIsLoggingOut(false)
    }
  }, [queryClient])

  const contextValue = useMemo(
    () => ({
      user,
      account,
      accountStatus: accountQuery.isError ? 'error' : account ? 'ready' : 'loading',
      isAuthenticated: Boolean(user),
      isInitialized,
      isKeycloak: Boolean(identity),
      isLoggingOut,
      token: keycloak.token || tokenManager.getToken(),
      setAccount,
      refreshAccount,
      loginWithKeycloak,
      logout,
    }),
    [
      user,
      account,
      accountQuery.isError,
      identity,
      isInitialized,
      isLoggingOut,
      setAccount,
      refreshAccount,
      loginWithKeycloak,
      logout,
    ],
  )

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
}

AuthProvider.propTypes = {
  children: PropTypes.node.isRequired,
}

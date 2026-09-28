/**
 * In-Memory Access Token Manager
 *
 * Security Rationale:
 * Storing JWT access tokens in localStorage exposes them directly to XSS token theft
 * (any compromised dependency or injected script can read localStorage.getItem()).
 *
 * Architecture:
 * 1. The short-lived Access Token resides exclusively in JavaScript closure memory.
 * 2. The long-lived Refresh Token resides in an HttpOnly, Secure, SameSite browser cookie.
 * 3. When the tab reloads or the access token expires, apiClient initiates a silent refresh.
 */

let inMemoryToken = null
let onTokenExpiredCallback = null

export const tokenManager = {
  /**
   * Retrieve the current in-memory access token
   * @returns {string|null}
   */
  getToken: () => inMemoryToken,

  /**
   * Store a fresh access token in memory
   * @param {string|null} token
   */
  setToken: (token) => {
    inMemoryToken = token
  },

  /**
   * Wipe token from memory on logout
   */
  clearToken: () => {
    inMemoryToken = null
  },

  /**
   * Check if an active token is present
   * @returns {boolean}
   */
  hasToken: () => Boolean(inMemoryToken),

  /**
   * Register a global listener for session expiration (401 unresolvable)
   * @param {Function} callback
   */
  onTokenExpired: (callback) => {
    onTokenExpiredCallback = callback
  },

  /**
   * Trigger the expired callback (redirect to login or clear auth context)
   */
  triggerTokenExpired: () => {
    inMemoryToken = null
    if (typeof onTokenExpiredCallback === 'function') {
      onTokenExpiredCallback()
    }
  },
}

export default tokenManager

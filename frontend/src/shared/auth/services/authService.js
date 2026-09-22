import apiClient from '@/shared/api/apiClient.js'
import { ENDPOINTS } from '@/shared/api/endpoints.js'
import tokenManager from '@/shared/api/tokenManager.js'

/**
 * Authentication Service
 *
 * Encapsulates all authentication network traffic.
 * Keeps tokens in memory while relying on HttpOnly session cookies.
 */
export const authService = {
  /**
   * Authenticate user with credentials
   * @param {{ email: string, password: string }} credentials
   * @returns {Promise<Object>} User session payload
   */
  login: async (credentials) => {
    const response = await apiClient.post(ENDPOINTS.AUTH.LOGIN, credentials)
    if (response?.accessToken) {
      tokenManager.setToken(response.accessToken)
    }
    return response
  },

  /**
   * Log out user on server and wipe in-memory access token
   */
  logout: async () => {
    try {
      await apiClient.post(ENDPOINTS.AUTH.LOGOUT)
    } finally {
      tokenManager.clearToken()
    }
  },

  /**
   * Perform silent token refresh (uses browser HttpOnly cookie)
   * @returns {Promise<string|null>}
   */
  refreshToken: async () => {
    try {
      const response = await apiClient.post(ENDPOINTS.AUTH.REFRESH)
      if (response?.accessToken) {
        tokenManager.setToken(response.accessToken)
        return response.accessToken
      }
      return null
    } catch {
      tokenManager.clearToken()
      return null
    }
  },

  /**
   * Retrieve currently authenticated user profile
   * @returns {Promise<Object>}
   */
  getCurrentUser: () => {
    return apiClient.get(ENDPOINTS.AUTH.ME)
  },
}

export default authService

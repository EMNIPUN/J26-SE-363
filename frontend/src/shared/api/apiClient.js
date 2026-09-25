import axios from 'axios'
import tokenManager from './tokenManager.js'
import ApiError from './apiError.js'
import { toast } from 'sonner'

/**
 * Production-Grade Centralized HTTP Client
 *
 * Capabilities:
 * - Relative zero-domain routing (/api)
 * - Automatic XSS-safe in-memory Bearer token injection
 * - HttpOnly cookie credential forwarding (withCredentials: true)
 * - Anti-CSRF header protection (X-Requested-With)
 * - Configurable request timeout
 * - Global error interception and normalization via ApiError
 */
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: Number(import.meta.env.VITE_API_TIMEOUT) || 15000,
  withCredentials: true, // Forwards HttpOnly session/refresh cookies automatically
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest', // Anti-CSRF protection
  },
})

// ---------------------------------------------------------------------------
// Request Interceptor: Auth Token & Trace Header Injection
// ---------------------------------------------------------------------------
apiClient.interceptors.request.use(
  (config) => {
    // 1. Inject in-memory access token if available
    const token = tokenManager.getToken()
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 2. Trace metadata
    config.headers['X-Client-Timestamp'] = new Date().toISOString()

    return config
  },
  (error) => Promise.reject(ApiError.fromAxiosError(error))
)

// ---------------------------------------------------------------------------
// Response Interceptor: Global Data Unwrapping & Error Firewall
// ---------------------------------------------------------------------------
apiClient.interceptors.response.use(
  (response) => {
    // Directly return response.data for cleaner consumer syntax
    return response.data
  },
  async (error) => {
    const apiError = ApiError.fromAxiosError(error)

    // Handle global HTTP status codes
    switch (apiError.status) {
      case 401:
        // Unauthorized: token expired or missing
        tokenManager.triggerTokenExpired()
        break

      case 403:
        // Forbidden: insufficient permissions
        toast.error('Access Denied: You do not have permission to perform this action.')
        break

      case 429:
        // Rate-limited
        toast.error('Too Many Requests: Please wait a moment before trying again.')
        break

      case 500:
      case 502:
      case 503:
      case 504:
        // Server infrastructure errors
        toast.error('Server Error: Our team has been notified. Please try again shortly.')
        break

      default:
        if (apiError.isNetworkError) {
          toast.error(apiError.message)
        }
        break
    }

    return Promise.reject(apiError)
  }
)

export default apiClient

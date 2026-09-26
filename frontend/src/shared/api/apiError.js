/**
 * Standardized ApiError
 *
 * Normalizes backend error payloads (e.g. FastAPI Pydantic validation errors,
 * Express/Django errors, network timeouts, CORS errors) into a unified, predictable structure.
 */
export class ApiError extends Error {
  constructor({
    message = 'An unexpected error occurred.',
    status = 500,
    code = 'UNKNOWN_ERROR',
    details = null,
    validationErrors = [],
    isNetworkError = false,
    rawError = null,
  }) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
    this.validationErrors = validationErrors
    this.isNetworkError = isNetworkError
    this.rawError = rawError
  }

  /**
   * Factory method to convert raw Axios errors into a normalized ApiError
   * @param {import('axios').AxiosError} error
   * @returns {ApiError}
   */
  static fromAxiosError(error) {
    if (!error.response) {
      const isTimeout = error.code === 'ECONNABORTED' || error.message?.includes('timeout')
      return new ApiError({
        message: isTimeout
          ? 'The request took too long to respond. Please check your connection.'
          : 'Unable to reach the server. Please verify your network connection.',
        status: 0,
        code: isTimeout ? 'REQUEST_TIMEOUT' : 'NETWORK_OFFLINE',
        isNetworkError: true,
        rawError: error,
      })
    }

    const { status, data } = error.response
    let message = 'An unexpected error occurred.'
    let code = `HTTP_${status}`
    let validationErrors = []

    if (typeof data === 'string') {
      message = data
    } else if (data && typeof data === 'object') {
      // Handles FastAPI/Pydantic validation errors: { detail: [{ loc: [...], msg: "..." }] }
      if (Array.isArray(data.detail)) {
        validationErrors = data.detail.map((err) => ({
          field: Array.isArray(err.loc) ? err.loc.join('.') : String(err.loc || ''),
          message: err.msg || 'Invalid field value',
        }))
        message = validationErrors.map((v) => `${v.field}: ${v.message}`).join(', ') || 'Validation error'
        code = 'VALIDATION_ERROR'
      } else if (typeof data.detail === 'string') {
        message = data.detail
      } else if (data.message) {
        message = data.message
      }

      if (data.code) {
        code = data.code
      }
    }

    return new ApiError({
      message,
      status,
      code,
      details: data,
      validationErrors,
      isNetworkError: false,
      rawError: error,
    })
  }
}

export default ApiError

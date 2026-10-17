import apiClient from '@/shared/api/apiClient'
import { ENDPOINTS } from '@/shared/api/endpoints'

export const accountKeys = { me: ['account'] }

export const accountService = {
  // GET: the signed-in person's account (created on first call), role and onboarding state
  getMe: () => apiClient.get(ENDPOINTS.ACCOUNT.ME),

  // POST: choose student or lecturer, give the details, accept the terms
  completeOnboarding: (payload) => apiClient.post(ENDPOINTS.ACCOUNT.ONBOARDING, payload),

  // PATCH: change details later (the role cannot change)
  updateProfile: (updates) => apiClient.patch(ENDPOINTS.ACCOUNT.PROFILE, updates),

  // PUT: the picture itself (a small JPEG) as the request body. DELETE: remove the upload.
  uploadPicture: (blob) =>
    apiClient.put(ENDPOINTS.ACCOUNT.PICTURE, blob, { headers: { 'Content-Type': blob.type } }),
  removePicture: () => apiClient.delete(ENDPOINTS.ACCOUNT.PICTURE),
}

export default accountService

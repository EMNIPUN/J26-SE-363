/** Public URL of the SELVIA Learning Assessment Platform (SLAP) student/lecturer app. */
export const SLAP_URL = (
  import.meta.env.VITE_SLAP_URL || 'http://localhost:5174'
).replace(/\/+$/, '')

export const SLAP_LOGIN_URL = `${SLAP_URL}/login`

/** Shared anchor props — always open SLAP in a new tab. */
export const SLAP_LINK_PROPS = Object.freeze({
  href: SLAP_LOGIN_URL,
  target: '_blank',
  rel: 'noopener noreferrer',
})

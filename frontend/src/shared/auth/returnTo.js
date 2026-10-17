// A person who opens an invitation link before finishing onboarding is sent to onboarding first.
// This remembers the page they wanted, for this browser tab only, so they land there afterwards.
const KEY = 'selvia-return-to'

export function rememberReturnTo(path) {
  try {
    sessionStorage.setItem(KEY, path)
  } catch {
    // storage can be unavailable; the person just lands on the home page instead
  }
}

export function takeReturnTo() {
  try {
    const path = sessionStorage.getItem(KEY)
    sessionStorage.removeItem(KEY)
    // Only in-app paths: never follow a stored address to another site.
    return path && path.startsWith('/') && !path.startsWith('//') ? path : null
  } catch {
    return null
  }
}

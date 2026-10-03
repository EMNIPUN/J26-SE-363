// External links come from the backend; only render absolute https URLs.
export function isSafeExternalUrl(url) {
  try {
    return new URL(url).protocol === 'https:'
  } catch {
    return false
  }
}

// Launch URLs for the embedded learning platform: https, or a path on this
// origin (the local stand-in app). Returns the resolved URL or null.
export function resolveEmbedUrl(url) {
  try {
    const resolved = new URL(url, window.location.href)
    const sameOrigin = resolved.origin === window.location.origin
    return resolved.protocol === 'https:' || sameOrigin ? resolved : null
  } catch {
    return null
  }
}

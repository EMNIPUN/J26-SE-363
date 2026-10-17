// Same rule as the Core API (backend/server/app/schemas/team.py): something@something.something
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

export function isEmail(value) {
  return EMAIL.test(value.trim()) && value.trim().length <= 320
}

/**
 * Splits pasted text into email addresses. Lines, commas, semicolons and spaces all separate them.
 * Addresses are lower-cased and listed once; anything that does not look like an address is
 * returned separately so it can be shown to the person instead of being dropped silently.
 */
export function parseEmails(text) {
  const valid = []
  const invalid = []
  for (const part of text.split(/[\s,;]+/)) {
    const entry = part.trim().toLowerCase()
    if (!entry) continue
    if (!isEmail(entry)) {
      if (!invalid.includes(entry)) invalid.push(entry)
    } else if (!valid.includes(entry)) {
      valid.push(entry)
    }
  }
  return { valid, invalid }
}

// GitHub logins: 1 to 39 letters, digits or single hyphens, not starting or ending with a hyphen.
const GITHUB_LOGIN = /^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$/

export function isGithubUsername(value) {
  return GITHUB_LOGIN.test(value.trim())
}

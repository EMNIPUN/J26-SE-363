const KEY = 'selvia-recent-teams'
const MAX = 5

/** Codes of the teams the person opened last, newest first. Only a convenience: never trusted. */
export function readRecentTeams() {
  try {
    const stored = JSON.parse(localStorage.getItem(KEY) ?? '[]')
    return Array.isArray(stored) ? stored.filter((code) => typeof code === 'string').slice(0, MAX) : []
  } catch {
    return []
  }
}

export function rememberTeam(code) {
  try {
    const next = [code, ...readRecentTeams().filter((other) => other !== code)].slice(0, MAX)
    localStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    // storage can be unavailable (private windows); the row is optional
  }
}

/**
 * Which teams this person has already passed the GitHub gate for, in this page load only.
 * It lives in memory, never in storage, so reloading the page starts the check again.
 */
const passed = new Set()
const key = (who, team) => `${who}|${String(team).toLowerCase()}`

export const hasPassed = (who, team) => passed.has(key(who, team))
export const markPassed = (who, team) => { passed.add(key(who, team)) }
export const forgetPassed = (who, team) => { passed.delete(key(who, team)) }

/** Where to go once the gate is passed: only ever a page inside the same team. */
export function safeNext(next, team) {
  const home = `/teams/${team}`
  if (typeof next !== 'string' || !next.startsWith('/') || next.startsWith('//')) return home
  const base = home.toLowerCase()
  const lower = next.toLowerCase()
  const inside = lower === base || lower.startsWith(`${base}/`) || lower.startsWith(`${base}?`)
  return inside && !lower.startsWith(`${base}/access`) ? next : home
}

/** The dedicated address of the access page, remembering where the person was going. */
export function accessHref(team, next) {
  const q = next && next !== `/teams/${team}` ? `?next=${encodeURIComponent(next)}` : ''
  return `/teams/${team}/access${q}`
}

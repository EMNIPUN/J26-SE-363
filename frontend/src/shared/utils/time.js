const MINUTE = 60 * 1000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

/** "just now", "5 min ago", "3 h ago", "2 d ago", then the date. */
export function timeAgo(value, now = Date.now()) {
  const age = now - new Date(value).getTime()
  if (age < MINUTE) return 'just now'
  if (age < HOUR) return `${Math.floor(age / MINUTE)} min ago`
  if (age < DAY) return `${Math.floor(age / HOUR)} h ago`
  if (age < 7 * DAY) return `${Math.floor(age / DAY)} d ago`
  return new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

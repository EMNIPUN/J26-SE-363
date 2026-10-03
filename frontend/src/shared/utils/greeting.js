const TITLES = ['Dr.', 'Prof.', 'Mr.', 'Mrs.', 'Ms.']

export function getGreeting(date = new Date()) {
  const hour = date.getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

// "Dr. Amara Silva" -> "Dr. Silva", "Nimal Perera" -> "Nimal"
export function getShortName(fullName = '') {
  const parts = fullName.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return 'there'
  if (TITLES.includes(parts[0]) && parts.length > 1) {
    return `${parts[0]} ${parts[parts.length - 1]}`
  }
  return parts[0]
}

export function formatToday(date = new Date()) {
  return date.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })
}

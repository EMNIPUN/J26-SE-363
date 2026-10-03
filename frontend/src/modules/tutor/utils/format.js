const shortDate = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' })

export function formatShortDate(isoDate) {
  if (!isoDate) return ''
  const date = new Date(isoDate)
  return Number.isNaN(date.getTime()) ? '' : shortDate.format(date)
}

const dateTime = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })

export function formatDateTime(isoDate) {
  if (!isoDate) return ''
  const date = new Date(isoDate)
  return Number.isNaN(date.getTime()) ? '' : dateTime.format(date)
}

const time = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit' })

export function formatTime(isoDate) {
  if (!isoDate) return ''
  const date = new Date(isoDate)
  return Number.isNaN(date.getTime()) ? '' : time.format(date)
}

export function formatDateRange(startIso, endIso) {
  const start = formatShortDate(startIso)
  const end = formatShortDate(endIso)
  if (start && end) return `${start} – ${end}`
  return start || end
}

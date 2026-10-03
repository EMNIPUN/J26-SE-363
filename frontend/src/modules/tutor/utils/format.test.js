import { describe, expect, it } from 'vitest'
import { formatDateRange, formatDateTime, formatShortDate, formatTime } from './format.js'

describe('date formatting', () => {
  it('returns an empty string for missing or invalid dates', () => {
    for (const format of [formatShortDate, formatDateTime, formatTime]) {
      expect(format(null)).toBe('')
      expect(format('not a date')).toBe('')
    }
  })

  it('formats a short day and month', () => {
    expect(formatShortDate('2026-10-02T12:00:00Z')).toBe('2 Oct')
  })

  it('joins a range and falls back to whichever end exists', () => {
    expect(formatDateRange('2026-10-01T12:00:00Z', '2026-10-14T12:00:00Z')).toBe('1 Oct – 14 Oct')
    expect(formatDateRange('2026-10-01T12:00:00Z', null)).toBe('1 Oct')
    expect(formatDateRange(null, null)).toBe('')
  })
})

import { describe, expect, it } from 'vitest'
import { timeAgo } from './time.js'

describe('timeAgo', () => {
  const now = new Date('2026-10-18T12:00:00Z').getTime()
  const ago = (ms) => new Date(now - ms).toISOString()

  it('says it the way people do', () => {
    expect(timeAgo(ago(10_000), now)).toBe('just now')
    expect(timeAgo(ago(5 * 60_000), now)).toBe('5 min ago')
    expect(timeAgo(ago(3 * 3_600_000), now)).toBe('3 h ago')
    expect(timeAgo(ago(2 * 86_400_000), now)).toBe('2 d ago')
  })

  it('shows a date after a week', () => {
    expect(timeAgo(ago(30 * 86_400_000), now)).toMatch(/\d/)
  })

  it('treats a time slightly in the future as just now', () => {
    expect(timeAgo(ago(-5_000), now)).toBe('just now')
  })
})

import { describe, expect, it } from 'vitest'
import { describeInvitation, formatDate } from './teams.js'

describe('describeInvitation', () => {
  it('says what the person is invited as', () => {
    expect(describeInvitation({ role: 'lecturer' })).toBe('as a lecturer')
    expect(describeInvitation({ role: 'member', as_leader: false })).toBe('as a team member')
    expect(describeInvitation({ role: 'member', as_leader: true })).toBe('as team leader')
  })
})

describe('formatDate', () => {
  it('shows a dash for nothing', () => {
    expect(formatDate(null)).toBe('—')
    expect(formatDate(undefined)).toBe('—')
  })

  it('formats a date', () => {
    expect(formatDate('2026-10-17T10:00:00Z')).toMatch(/2026/)
  })
})

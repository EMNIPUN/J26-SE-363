import { describe, expect, it } from 'vitest'
import { describeInvitation, formatDate, needsAttention } from './teams.js'

const team = (over) => ({
  id: 't1',
  name: 'Atlas',
  student_count: 3,
  leader: { name: 'Sam' },
  repo_url: 'https://github.com/x/y',
  pending_invitations: 0,
  my_role: 'lecturer',
  ...over,
})

describe('needsAttention', () => {
  it('has nothing to say about a finished team', () => {
    expect(needsAttention([team()], true)).toEqual([])
  })

  it('lists each gap of a team for lecturers', () => {
    const items = needsAttention([team({ leader: null, repo_url: null, pending_invitations: 2 })], true)
    expect(items.map((item) => item.message)).toEqual([
      'has no leader yet',
      'has no repository linked',
      'has 2 invitations waiting for a reply',
    ])
  })

  it('does not ask for a leader before any student is in the team', () => {
    expect(needsAttention([team({ student_count: 0, leader: null })], true)).toEqual([])
  })

  it('says "1 invitation" in the singular', () => {
    expect(needsAttention([team({ pending_invitations: 1 })], true)[0].message).toMatch(/1 invitation waiting/)
  })

  it('only asks a team leader to link the repository', () => {
    const open = { repo_url: null, pending_invitations: 3 }
    expect(needsAttention([team({ ...open, my_role: 'member' })], false)).toEqual([])
    expect(needsAttention([team({ ...open, my_role: 'leader' })], false).map((i) => i.message)).toEqual([
      'needs a repository link',
    ])
  })
})

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

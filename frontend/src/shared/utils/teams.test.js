import { describe, expect, it } from 'vitest'
import {
  ageLabel,
  daysSince,
  describeInvitation,
  formatDate,
  latestTerm,
  needsAttention,
  profileChecklist,
  splitByTerm,
  teamHref,
} from './teams.js'

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

describe('teamHref', () => {
  it('opens a team, or its setup while it is pending', () => {
    expect(teamHref({ code: 'A-1', status: 'active' })).toBe('/teams/A-1/app')
    expect(teamHref({ code: 'A-1', status: 'pending' })).toBe('/teams/new/A-1')
  })
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

  it('leaves a team that is still being set up to its own card', () => {
    expect(needsAttention([team({ status: 'pending', repo_url: null, leader: null })], true)).toEqual([])
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

describe('terms', () => {
  const at = (term, status = 'active') => ({ term, status })

  it('finds the latest term among teams that are set up', () => {
    expect(latestTerm([at('2025-S2'), at('2026-S1'), at('2026-S2', 'pending')])).toBe('2026-S1')
    expect(latestTerm([])).toBeNull()
  })

  it('splits teams into the latest term and the rest, keeping drafts with the current ones', () => {
    const old = at('2025-S2')
    const now = at('2026-S1')
    const draft = at('2026-S2', 'pending')
    expect(splitByTerm([old, now, draft])).toEqual({ latest: '2026-S1', current: [now, draft], earlier: [old] })
  })
})

describe('profileChecklist', () => {
  const account = { picture: null, email_verified: true, profile: { institution: ' ', student_number: '', department: 'CS' } }

  it('marks what is filled in, ignoring blanks', () => {
    const items = profileChecklist(account, 'instructor')
    expect(items.map((i) => [i.key, i.done])).toEqual([
      ['picture', false],
      ['institution', false],
      ['department', true],
      ['email', true],
    ])
  })

  it('asks students for a student number and lecturers for a department', () => {
    expect(profileChecklist(account, 'student').map((i) => i.key)).toContain('number')
    expect(profileChecklist(account, 'instructor').map((i) => i.key)).toContain('department')
  })
})

describe('waiting time', () => {
  const now = new Date('2026-10-17T12:00:00Z').getTime()

  it('counts whole days', () => {
    expect(daysSince('2026-10-17T01:00:00Z', now)).toBe(0)
    expect(daysSince('2026-10-14T11:00:00Z', now)).toBe(3)
    expect(daysSince('2026-10-30T00:00:00Z', now)).toBe(0) // a date in the future is not negative
  })

  it('says it in words', () => {
    expect([ageLabel(0), ageLabel(1), ageLabel(6)]).toEqual(['today', '1 day', '6 days'])
  })
})

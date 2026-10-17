import { beforeEach, describe, expect, it } from 'vitest'
import { readRecentTeams, rememberTeam } from './recentTeams.js'

function stubStorage() {
  const store = new Map()
  globalThis.localStorage = {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
  }
}

describe('recent teams', () => {
  beforeEach(stubStorage)

  it('lists the newest first and each team once', () => {
    rememberTeam('A')
    rememberTeam('B')
    rememberTeam('A')
    expect(readRecentTeams()).toEqual(['A', 'B'])
  })

  it('keeps five', () => {
    for (const code of ['A', 'B', 'C', 'D', 'E', 'F']) rememberTeam(code)
    expect(readRecentTeams()).toEqual(['F', 'E', 'D', 'C', 'B'])
  })

  it('ignores damaged storage and an unavailable one', () => {
    localStorage.setItem('selvia-recent-teams', '{not json')
    expect(readRecentTeams()).toEqual([])
    localStorage.setItem('selvia-recent-teams', '[1, "ok", null]')
    expect(readRecentTeams()).toEqual(['ok'])
    delete globalThis.localStorage
    expect(() => rememberTeam('A')).not.toThrow()
    expect(readRecentTeams()).toEqual([])
  })
})

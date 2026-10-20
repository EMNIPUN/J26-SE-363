import { describe, expect, it } from 'vitest'
import { getNavForRole } from './navConfig.js'

describe('the lecturer navigation', () => {
  const nav = getNavForRole('instructor', 'MC01')
  it('has the assessment tabs as sub tabs of Team, in place of "Team assessment"', () => {
    const team = nav.find((s) => s.label === 'Team')
    expect(team.children.map((c) => c.label)).toEqual(['Members', 'Results', 'Development', 'Runs', 'Reviews', 'Setup'])
    expect(team.children.map((c) => c.to)).toContain('/teams/MC01/performance/team/runs')
    expect(JSON.stringify(nav)).not.toContain('Team assessment')
  })
  it('keeps the method page reachable', () => {
    expect(nav.find((s) => s.label === 'Method and weights').to).toBe('/teams/MC01/performance/method')
  })
})

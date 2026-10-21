import { describe, expect, it } from 'vitest'
import { gateCopy, reasonText, stepStates } from './gateCopy.js'

describe('the three steps', () => {
  it('moves along as the person gets further', () => {
    expect(stepStates({ state: 'repo_not_linked' })).toEqual(['current', 'waiting', 'waiting'])
    expect(stepStates({ state: 'account_not_linked' })).toEqual(['done', 'current', 'waiting'])
    expect(stepStates({ state: 'read_only' })).toEqual(['done', 'done', 'failed'])
    expect(stepStates({ state: 'no_access' })).toEqual(['done', 'done', 'failed'])
    expect(stepStates({ state: 'github_unavailable' })).toEqual(['done', 'done', 'current'])
    expect(stepStates({ state: 'ok' })).toEqual(['done', 'done', 'done'])
  })
})

describe('what the gate says', () => {
  it('asks the leader to link and tells a member whom they wait for', () => {
    expect(gateCopy({ state: 'repo_not_linked', is_leader: true }, 'MediCare').primary).toBe('repo')
    const m = gateCopy({ state: 'repo_not_linked', is_leader: false, leader_name: 'Sam' }, 'MediCare')
    expect(m.title).toBe('Waiting for your team leader')
    expect(m.body).toContain('Sam')
    expect(m.primary).toBe('recheck')
  })

  it('asks for the GitHub account, and explains a rejected one with a way to use another', () => {
    expect(gateCopy({ state: 'account_not_linked' }, 'MediCare').title).toContain('MediCare')
    const r = gateCopy({ state: 'no_access', login: 'ann-dev', leader_name: 'Sam' }, 'MediCare')
    expect(r.tone).toBe('reject')
    expect(r.title).toContain('@ann-dev')
    expect(r.secondary).toBe('switch')
    expect(gateCopy({ state: 'read_only', login: 'bob' }, 'x').body).toContain('write access')
  })

  it('does not blame the person when GitHub cannot be reached', () => {
    expect(gateCopy({ state: 'github_unavailable' }, 'x').body).toContain('Nothing is wrong with your account')
  })

  it('explains why a sign-in came back with an error', () => {
    expect(reasonText('github_account_taken')).toContain('only one team member')
    expect(reasonText('whatever')).toContain('Try again')
  })
})

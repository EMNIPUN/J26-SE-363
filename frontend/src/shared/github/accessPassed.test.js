import { describe, expect, it } from 'vitest'
import { accessHref, forgetPassed, hasPassed, markPassed, safeNext } from './accessPassed.js'

describe('the memory of a passed gate', () => {
  it('is per person and per team, and can be taken back', () => {
    expect(hasPassed('a@x', 'MC01')).toBe(false)
    markPassed('a@x', 'MC01')
    expect(hasPassed('a@x', 'mc01')).toBe(true)
    expect(hasPassed('b@x', 'MC01')).toBe(false)
    expect(hasPassed('a@x', 'MC02')).toBe(false)
    forgetPassed('a@x', 'MC01')
    expect(hasPassed('a@x', 'MC01')).toBe(false)
  })
})

describe('where to go after the gate', () => {
  it('stays inside the team', () => {
    expect(safeNext('/teams/MC01/performance/runs', 'MC01')).toBe('/teams/MC01/performance/runs')
    expect(safeNext('/teams/MC02/app', 'MC01')).toBe('/teams/MC01')
    expect(safeNext('https://evil.example', 'MC01')).toBe('/teams/MC01')
    expect(safeNext('//evil.example/teams/MC01', 'MC01')).toBe('/teams/MC01')
    expect(safeNext('/teams/MC01/access', 'MC01')).toBe('/teams/MC01')
    expect(safeNext(null, 'MC01')).toBe('/teams/MC01')
  })
  it('builds the access address with where the person was going', () => {
    expect(accessHref('MC01', '/teams/MC01')).toBe('/teams/MC01/access')
    expect(accessHref('MC01', '/teams/MC01/members')).toBe('/teams/MC01/access?next=%2Fteams%2FMC01%2Fmembers')
  })
})

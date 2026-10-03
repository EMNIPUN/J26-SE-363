import { describe, expect, it } from 'vitest'
import { getActionPath, getTutorPaths } from './tutorPaths.js'

describe('getTutorPaths', () => {
  it('builds every tutor route under the team', () => {
    const paths = getTutorPaths('team-7')

    expect(paths.chat).toBe('/teams/team-7/tutor/chat')
    expect(paths.sprintGuidance).toBe('/teams/team-7/tutor/learning')
    expect(paths.activity('act-quiz-jwt')).toBe('/teams/team-7/tutor/activity/act-quiz-jwt')
    expect(paths.results('asm-1')).toBe('/teams/team-7/tutor/results/asm-1')
  })
})

describe('getActionPath', () => {
  const paths = getTutorPaths('team-7')

  it('maps an activity action to the activity page', () => {
    expect(getActionPath(paths, { kind: 'activity', targetId: 'act-ex-jwt-middleware' })).toBe(
      '/teams/team-7/tutor/activity/act-ex-jwt-middleware',
    )
  })

  it('returns null for missing or unknown actions', () => {
    expect(getActionPath(paths, null)).toBeNull()
    expect(getActionPath(paths, { kind: 'lesson', targetId: 'x' })).toBeNull()
  })
})

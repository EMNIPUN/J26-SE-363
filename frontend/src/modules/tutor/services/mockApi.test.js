import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import mockApi from './mockApi.js'
import { MAX_MESSAGE_LENGTH } from '../utils/constants.js'

const COMPLETIONS_KEY = 'selvia-mock-learning-app-completions'
const FAILURE_KEY = 'selvia-tutor-mock-fail'

// Resolves a mock API call by fast-forwarding its simulated latency.
async function call(promise) {
  const settled = promise.then(
    (value) => ({ value }),
    (error) => ({ error }),
  )
  await vi.runAllTimersAsync()
  const { value, error } = await settled
  if (error) throw error
  return value
}

// What the embedded learning app does when the student finishes an activity.
function reportCompletion(activityId) {
  const completions = JSON.parse(sessionStorage.getItem(COMPLETIONS_KEY) ?? '[]')
  sessionStorage.setItem(COMPLETIONS_KEY, JSON.stringify([...completions, activityId]))
}

async function completeActivity(activityId) {
  reportCompletion(activityId)
  return call(mockApi.syncActivityResult(activityId))
}

const byId = (items, key = 'conceptId') => Object.fromEntries(items.map((item) => [item[key], item]))

beforeEach(async () => {
  vi.useFakeTimers()
  await call(mockApi.resetSession())
})

afterEach(() => {
  vi.useRealTimers()
})

describe('knowledge gaps', () => {
  it('classifies each concept against its requirement and sorts by severity', async () => {
    const gaps = await call(mockApi.getKnowledgeGaps())

    expect(gaps.map((g) => [g.conceptId, g.status, g.gap])).toEqual([
      ['token-validation', 'major_gap', 42],
      ['jwt', 'major_gap', 38],
      ['authorization', 'moderate_gap', 9],
      ['authentication', 'moderate_gap', 7],
      ['rest-api', 'sufficient', 0],
    ])
  })

  it('reports required knowledge in the same shape as the gaps', async () => {
    const required = byId(await call(mockApi.getRequiredKnowledge()))

    expect(required.jwt).toMatchObject({ name: 'JWT', required: 80, current: 42, status: 'major_gap' })
  })
})

describe('sprint guidance suggestions', () => {
  it('suggests learning material, practice and web resources for a major gap', async () => {
    const { concepts } = await call(mockApi.getSprintGuidance())
    const { suggestions } = byId(concepts)['token-validation']

    expect(suggestions.learning.length).toBeGreaterThan(0)
    expect(suggestions.learning.every((i) => i.kind === 'learning')).toBe(true)
    expect(new Set(suggestions.practice.map((i) => i.kind))).toEqual(new Set(['exercise', 'quiz']))
    expect(suggestions.webResources.length).toBeGreaterThan(0)
    expect(suggestions.challenge).toBeUndefined()
  })

  it('suggests only adaptive quizzes and coding exercises for a small gap', async () => {
    const { concepts } = await call(mockApi.getSprintGuidance())
    const { suggestions } = byId(concepts).authorization

    expect(suggestions.learning).toBeUndefined()
    expect(suggestions.webResources).toBeUndefined()
    expect(suggestions.practice.map((i) => i.kind)).toEqual(['quiz', 'exercise'])
    expect(suggestions.practice.some((i) => i.challenge)).toBe(false)
  })

  it('offers only an optional challenge when the requirement is met', async () => {
    const { concepts } = await call(mockApi.getSprintGuidance())
    const { suggestions, suggestionSummary } = byId(concepts)['rest-api']

    expect(Object.keys(suggestions)).toEqual(['challenge'])
    expect(suggestions.challenge.every((i) => i.challenge && i.kind === 'quiz')).toBe(true)
    expect(suggestionSummary).toMatch(/no action needed/i)
  })

  it('focuses the plan on the recommended concept', async () => {
    const guidance = await call(mockApi.getSprintGuidance())
    const recommendation = await call(mockApi.getRecommendation())

    expect(guidance.focusConceptId).toBe(recommendation.conceptId)
  })
})

describe('recommendation', () => {
  it('starts with learning material at the student level for the largest gap', async () => {
    const recommendation = await call(mockApi.getRecommendation())

    expect(recommendation).toMatchObject({
      conceptId: 'token-validation',
      type: 'learning',
      action: { kind: 'activity', targetId: 'act-token-expiration' },
    })
    expect(recommendation.reasons).toHaveLength(4)
    expect(recommendation.reasons.join(' ')).not.toMatch(/\{\w+\}/)
  })

  it('marks exactly one activity as recommended across the guidance', async () => {
    const { concepts } = await call(mockApi.getSprintGuidance())
    const recommended = concepts
      .flatMap((c) => Object.values(c.suggestions).flat())
      .filter((item) => item.recommended)

    expect(recommended).toHaveLength(1)
  })
})

describe('activity catalogue', () => {
  it('offers challenge quizzes only for concepts that meet their requirement', async () => {
    const catalog = await call(mockApi.getActivityCatalog('quiz'))

    for (const group of catalog.concepts) {
      const hasChallenge = group.items.some((i) => i.challenge)
      expect(hasChallenge).toBe(group.status === 'sufficient')
    }
  })

  it('marks a kind as suggested only where the gap status calls for it', async () => {
    const quizzes = byId((await call(mockApi.getActivityCatalog('quiz'))).concepts)
    const exercises = byId((await call(mockApi.getActivityCatalog('exercise'))).concepts)

    expect(quizzes.jwt.suggested).toBe(true)
    expect(quizzes.authorization.suggested).toBe(true)
    expect(quizzes['rest-api'].suggested).toBe(false)
    expect(exercises.authentication.suggested).toBe(true)
  })

  it('rejects an unknown activity kind', async () => {
    await expect(call(mockApi.getActivityCatalog('video'))).rejects.toMatchObject({ status: 400 })
  })
})

describe('embedded activity', () => {
  it('returns a same-origin launch URL that identifies the activity', async () => {
    const activity = await call(mockApi.getActivity('act-quiz-jwt'))
    const url = new URL(activity.launchUrl, window.location.href)

    expect(url.origin).toBe(window.location.origin)
    expect(url.searchParams.get('activityId')).toBe('act-quiz-jwt')
    expect(activity).toMatchObject({ concept: { id: 'jwt' }, platform: { name: 'Learning Lab' } })
  })

  it('rejects an unknown activity', async () => {
    await expect(call(mockApi.getActivity('act-missing'))).rejects.toMatchObject({ status: 404 })
    await expect(call(mockApi.syncActivityResult('act-missing'))).rejects.toMatchObject({ status: 404 })
  })
})

describe('activity result sync', () => {
  it('reports in progress until the learning platform reports a completion', async () => {
    const sync = await call(mockApi.syncActivityResult('act-quiz-jwt'))
    const gaps = byId(await call(mockApi.getKnowledgeGaps()))

    expect(sync).toEqual({ status: 'in_progress', activityId: 'act-quiz-jwt' })
    expect(gaps.jwt.current).toBe(42)
  })

  it('turns a completed quiz into new evidence and an updated competency', async () => {
    const sync = await completeActivity('act-quiz-jwt')
    const { result } = sync

    expect(sync.status).toBe('completed')
    expect(result).toMatchObject({
      score: 76,
      band: 'developing',
      primaryConcept: { id: 'jwt' },
      confidence: { before: 81, after: 83 },
      evidence: { before: 7, after: 8 },
    })
    expect(result.conceptPerformance.map((c) => [c.conceptId, c.score, c.band])).toEqual([
      ['jwt', 76, 'developing'],
      ['token-validation', 64, 'developing'],
    ])
    expect(byId(result.changes).jwt).toMatchObject({ before: 42, after: 52, gapBefore: 38, gapAfter: 28 })
    expect(byId(result.changes)['token-validation']).toMatchObject({ before: 38, after: 42 })

    const gaps = byId(await call(mockApi.getKnowledgeGaps()))
    expect(gaps.jwt.current).toBe(52)
  })

  it('applies each reported completion only once', async () => {
    await completeActivity('act-quiz-jwt')
    const second = await call(mockApi.syncActivityResult('act-quiz-jwt'))
    const gaps = byId(await call(mockApi.getKnowledgeGaps()))

    expect(second.status).toBe('in_progress')
    expect(gaps.jwt.current).toBe(52)
  })

  it('ignores completions reported for a different activity', async () => {
    reportCompletion('act-quiz-authorization')
    const sync = await call(mockApi.syncActivityResult('act-quiz-jwt'))

    expect(sync.status).toBe('in_progress')
  })

  it('records when a result closes a knowledge gap', async () => {
    const { result } = await completeActivity('act-ex-role-middleware')
    const [history] = await call(mockApi.getAssessmentHistory())

    expect(byId(result.changes).authorization).toMatchObject({ statusBefore: 'moderate_gap', statusAfter: 'sufficient' })
    expect(history).toMatchObject({ activityId: 'act-ex-role-middleware', primaryGain: 10, gapsClosed: 1 })
  })

  it('stores the result for the results page and the progress history', async () => {
    const { assessmentId } = await completeActivity('act-quiz-jwt')

    const stored = await call(mockApi.getUpdatedCompetency(assessmentId))
    const history = await call(mockApi.getAssessmentHistory())

    expect(stored.assessmentId).toBe(assessmentId)
    expect(history).toHaveLength(1)
    expect(history[0]).toMatchObject({ assessmentId, score: 76, primaryGain: 10, gapsClosed: 0 })
    await expect(call(mockApi.getUpdatedCompetency('asm-missing'))).rejects.toMatchObject({ status: 404 })
  })

  it('posts the result and the next step to the tutor chat', async () => {
    const { result } = await completeActivity('act-quiz-jwt')
    const conversation = await call(mockApi.getTutorConversation())
    const message = conversation.at(-1)

    expect(message.role).toBe('tutor')
    expect(message.content).toContain('76%')
    expect(message.action).toEqual(result.nextRecommendation.action)
    expect(message.context.competency).toBe(52)
  })

  it('moves the learning loop on to the new evidence', async () => {
    const before = byId((await call(mockApi.getLearningLoop())).steps, 'id')
    const { assessmentId } = await completeActivity('act-quiz-jwt')
    const after = await call(mockApi.getLearningLoop())
    const steps = byId(after.steps, 'id')

    expect(before.evidence.status).toBe('upcoming')
    expect(steps.evidence.status).toBe('done')
    expect(steps.updated.detail).toContain('42')
    expect(steps.updated.detail).toContain('52')
    expect(after.latestAssessmentId).toBe(assessmentId)
  })
})

describe('learning loop', () => {
  it('has exactly one current step', async () => {
    const { steps } = await call(mockApi.getLearningLoop())

    expect(steps.filter((s) => s.status === 'current')).toHaveLength(1)
  })

  it('skips learning material once the focus concept only has a small gap', async () => {
    // Raise both major gaps to small gaps so the focus becomes a moderate gap.
    for (const id of ['act-ex-token-errors', 'act-quiz-token-validation', 'act-signature-validation', 'act-token-expiration']) {
      await completeActivity(id)
    }
    for (const id of ['act-ex-jwt-middleware', 'act-quiz-jwt', 'act-jwt-implementation']) {
      await completeActivity(id)
    }
    const gaps = await call(mockApi.getKnowledgeGaps())
    const { steps } = await call(mockApi.getLearningLoop())

    expect(gaps.some((g) => g.status === 'major_gap')).toBe(false)
    expect(byId(steps, 'id').learning.status).toBe('skipped')
  })
})

describe('full adaptive workflow', () => {
  it('closes every knowledge gap by following the recommendations', async () => {
    const followed = []
    for (let step = 0; step < 40; step += 1) {
      const recommendation = await call(mockApi.getRecommendation())
      if (!recommendation) break
      followed.push(recommendation.action.targetId)
      await completeActivity(recommendation.action.targetId)
    }

    const gaps = await call(mockApi.getKnowledgeGaps())
    const loop = await call(mockApi.getLearningLoop())
    const guidance = await call(mockApi.getSprintGuidance())

    expect(gaps.every((g) => g.status === 'sufficient')).toBe(true)
    expect(await call(mockApi.getRecommendation())).toBeNull()
    expect(followed.length).toBeLessThan(40)
    expect(loop.focusConcept).toBeNull()
    expect(guidance.focusConceptId).toBeNull()
    expect(loop.steps.filter((s) => s.status === 'current')).toHaveLength(0)
    expect(guidance.concepts.every((c) => Object.keys(c.suggestions).join() === 'challenge')).toBe(true)
  })
})

describe('tutor chat', () => {
  it('stores the student message and the tutor reply', async () => {
    const before = await call(mockApi.getTutorConversation())
    const { message, reply } = await call(mockApi.sendTutorMessage({ message: '  What is JWT?  ' }))
    const after = await call(mockApi.getTutorConversation())

    expect(message).toMatchObject({ role: 'student', content: 'What is JWT?' })
    expect(reply.role).toBe('tutor')
    expect(after).toHaveLength(before.length + 2)
  })

  it('answers a quick action with its prompt as the student message', async () => {
    const [quickAction] = await call(mockApi.getQuickActions())
    const { message } = await call(mockApi.sendTutorMessage({ quickActionId: quickAction.id }))

    expect(message.content).toBe(quickAction.prompt)
  })

  it('validates the message', async () => {
    await expect(call(mockApi.sendTutorMessage({ message: '   ' }))).rejects.toMatchObject({ status: 422 })
    await expect(
      call(mockApi.sendTutorMessage({ message: 'a'.repeat(MAX_MESSAGE_LENGTH + 1) })),
    ).rejects.toMatchObject({ status: 422 })
    await expect(call(mockApi.sendTutorMessage({ quickActionId: 'nope' }))).rejects.toMatchObject({ status: 400 })
  })
})

describe('session', () => {
  it('reset restores the starting competencies and clears platform completions', async () => {
    await completeActivity('act-quiz-jwt')
    reportCompletion('act-quiz-jwt')

    await call(mockApi.resetSession())
    const gaps = byId(await call(mockApi.getKnowledgeGaps()))

    expect(gaps.jwt.current).toBe(42)
    expect(await call(mockApi.getAssessmentHistory())).toEqual([])
    expect(sessionStorage.getItem(COMPLETIONS_KEY)).toBeNull()
  })

  it('returns copies so callers cannot change the stored session', async () => {
    const gaps = await call(mockApi.getKnowledgeGaps())
    gaps[0].current = 100

    const again = await call(mockApi.getKnowledgeGaps())
    expect(again[0].current).toBe(38)
  })

  it('simulates a server error for the functions listed in session storage', async () => {
    sessionStorage.setItem(FAILURE_KEY, 'getRecommendation')

    await expect(call(mockApi.getRecommendation())).rejects.toMatchObject({ status: 500, name: 'ApiError' })
    await expect(call(mockApi.getKnowledgeGaps())).resolves.toHaveLength(5)
  })
})

import { describe, expect, it } from 'vitest'
import { band, contributions, duration, explainFactor, explainMark, factorState, initials, markBand, markText, questionsOf, quizSummary, rangeText, summarize } from './format.js'

describe('bands and text', () => {
  it('cuts scores at the same points as the justification', () => {
    expect([band(0.1), band(0.34), band(0.66), band(0.67), band(null)]).toEqual(['low', 'medium', 'medium', 'high', null])
    expect(markBand(70)).toBe('high')
    expect(markText(null)).toBe('n/a')
    expect(markText(71.6)).toBe('72')
    expect(rangeText([52.2, 91.7])).toBe('52 to 92')
    expect(rangeText(null)).toBe('')
  })

  it('names a factor with no score instead of showing a zero', () => {
    expect(factorState({ status: 'completed', score: 0.5 }).kind).toBe('scored')
    expect(factorState({ status: 'completed', score: 0 }).kind).toBe('scored') // a real 0
    expect(factorState({ status: 'not_available' }).label).toBe('Cannot be measured')
    expect(factorState({ status: 'pending' }).kind).toBe('pending')
    expect(factorState({ status: 'fallback' }).kind).toBe('failed')
    expect(factorState(undefined).kind).toBe('missing')
  })

  it('formats durations and initials', () => {
    expect([duration(12), duration(75), duration(3700)]).toEqual(['12 s', '1 min 15 s', '1 h 1 min'])
    expect(initials('Sadeesha Sathsara Kumbukage')).toBe('SS')
    expect(initials('')).toBe('?')
  })
})

describe('contributions', () => {
  const weights = { effort: 0.2, consistency: 0.15, requirement_fulfillment: 0.25, collaboration: 0.15, task_complexity: 0.1, code_ownership: 0.15 }

  it('shares the weight of a missing factor among the others, so the points add up to the mark', () => {
    const factors = {
      effort: { status: 'completed', score: 0.6 }, consistency: { status: 'completed', score: 0.5 }, requirement_fulfillment: { status: 'completed', score: 0.7 },
      collaboration: { status: 'not_available', score: null }, task_complexity: { status: 'completed', score: 0.5 }, code_ownership: { status: 'pending', score: null },
    }
    const parts = contributions(factors, weights)
    expect(parts.map((p) => p.id)).toEqual(['effort', 'consistency', 'requirement_fulfillment', 'task_complexity'])
    expect(parts.reduce((a, p) => a + p.weight, 0)).toBeCloseTo(1)
    const expected = (100 * (0.2 * 0.6 + 0.15 * 0.5 + 0.25 * 0.7 + 0.1 * 0.5)) / 0.7
    expect(parts.reduce((a, p) => a + p.points, 0)).toBeCloseTo(expected)
  })

  it('has nothing to show when no factor was scored', () => {
    expect(contributions({ effort: { status: 'not_available' } }, weights)).toEqual([])
    expect(contributions(undefined, undefined)).toEqual([])
  })
})

describe('summarize', () => {
  it('counts what needs the lecturer', () => {
    const rows = [
      { effective_mark: 80, status: 'final', factors: { code_ownership: { status: 'completed' } }, justification: { flags: [] } },
      { effective_mark: 40, status: 'pending_review', factors: { code_ownership: { status: 'pending' } }, justification: { flags: [{}, {}] } },
      { effective_mark: null, status: 'provisional', factors: {}, justification: {} },
    ]
    expect(summarize(rows)).toMatchObject({ students: 3, mean: 60, lowest: 40, highest: 80, needReview: 1, provisional: 1, waitingForAnswer: 1, flags: 2 })
    expect(summarize([]).mean).toBeNull()
  })
})

describe('why this mark', () => {
  const weights = { effort: 0.2, consistency: 0.15, requirement_fulfillment: 0.25, collaboration: 0.15, task_complexity: 0.1, code_ownership: 0.15 }
  const result = {
    mark: 61, effective_mark: 61, mark_interval: [45, 76],
    factors: {
      effort: { status: 'completed', score: 0.82, provisional: true }, consistency: { status: 'completed', score: 0.3, provisional: true }, requirement_fulfillment: { status: 'completed', score: 0.6, provisional: true },
      collaboration: { status: 'not_available', score: null }, task_complexity: { status: 'completed', score: 0.5 }, code_ownership: { status: 'pending', score: null },
      behavioral_pattern: { persona: 'Burst worker', applied: true, modifier: 0.94 },
    },
    justification: { flags: [{ message: 'x' }], factors: { collaboration: { reasons: ['Nobody reviewed anything in this sprint.'] } } },
  }

  it('names what added the most, what held the mark back and what was left out', () => {
    const { headline, lines } = explainMark(result, weights)
    expect(headline).toBe('61 out of 100: a moderate contribution')
    const text = lines.map((l) => l.text).join(' | ')
    expect(text).toContain('Effort added the most')
    expect(text).toContain('Consistency held the mark back most: a score of 30, which is low')
    expect(text).toContain('Collaboration is not part of the mark: Nobody reviewed anything in this sprint.')
    expect(text).toContain('Code Ownership is not part of the mark: waiting for the answer')
    expect(text).toContain('adjusted the total by a factor of 0.94')
    expect(text).toContain('The likely range is 45 to 76')
    expect(text).toContain('still running')
    expect(text).toContain('1 point need a person')
  })

  it('says nothing about a student who has no result', () => {
    expect(explainMark(null, weights)).toEqual({ headline: '', lines: [] })
  })

  it('explains one factor card in a sentence', () => {
    const part = contributions(result.factors, weights).find((p) => p.id === 'effort')
    expect(explainFactor({}, result.factors.effort, part)).toMatch(/Scored 82 out of 100, which is high\. It counts for \d+% of the mark and added [\d.]+ points\./)
    expect(explainFactor({}, result.factors.collaboration)).toContain('left out of the mark')
    expect(explainFactor({}, result.factors.code_ownership)).toContain('Waiting for')
  })
})

describe('the code questions', () => {
  it('turns one question or many into a list', () => {
    expect(questionsOf(null)).toEqual([])
    expect(questionsOf({ question: 'a' })).toHaveLength(1)
    expect(questionsOf({ questions: [{ question: 'a' }, { question: 'b' }] }).map((q) => q.n)).toEqual([1, 2])
  })
  it('counts how it went', () => {
    const s = quizSummary([{ status: 'answered', rating: 4 }, { status: 'answered', rating: 2 }, { status: 'open' }, { status: 'expired' }])
    expect(s).toEqual({ total: 4, answered: 2, open: 1, expired: 1, average: 3 })
    expect(quizSummary([]).average).toBeNull()
  })
})

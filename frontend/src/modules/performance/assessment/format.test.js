import { describe, expect, it } from 'vitest'
import { band, contributions, duration, explainFactor, explainMark, factorState, initials, markBand, markText, briefOf, evidenceOf, factorHistory, questionsOf, quizSummary, radarData, rangeText, summarize, teamAverage, TRACKED } from './format.js'

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
  const sc = (score) => ({ status: 'completed', score, provisional: true })
  const result = {
    mark: 61, effective_mark: 61, mark_interval: [45, 76],
    factors: {
      effort: { status: 'completed', score: 0.82, provisional: true }, consistency: { status: 'completed', score: 0.3, provisional: true }, requirement_fulfillment: { status: 'completed', score: 0.6, provisional: true },
      collaboration: { status: 'not_available', score: null }, task_complexity: { status: 'completed', score: 0.5 }, code_ownership: { status: 'pending', score: null },
      behavioral_pattern: { persona: 'Burst worker', applied: true, modifier: 0.94 },
    },
    justification: { flags: [{ message: 'x' }], factors: { collaboration: { reasons: ['Nobody reviewed anything in this sprint.'] } } },
  }

  it('puts the three things that matter most first, each with a lead word, and the rest after', () => {
    const { headline, key, more } = explainMark(result, weights)
    expect(headline).toBe('61 out of 100: a moderate contribution')
    expect(key.map((l) => l.lead)).toEqual(['Biggest strength', 'Held back by', 'To check'])
    expect(key[0].text).toContain('Effort')
    expect(key[1].text).toBe('Consistency: score 30, low')
    const rest = more.map((l) => `${l.lead}: ${l.text}`).join(' | ')
    expect(rest).toContain('Left out: Collaboration, Code Ownership. Their weight goes to the other factors')
    expect(rest).toContain('Burst worker: adjusted the total by 0.94')
    expect(rest).toContain('Likely 45 to 76')
    expect(rest).toContain('Still running')
  })

  it('says why a single left-out factor is left out', () => {
    const one = { ...result, factors: { ...result.factors, code_ownership: sc(0.7) } }
    const out = [...explainMark(one, weights).key, ...explainMark(one, weights).more].find((l) => l.kind === 'out')
    expect(out.text).toContain('Collaboration')
    expect(out.text).toContain('nobody reviewed anything in this sprint')
  })

  it('says nothing about a student who has no result', () => {
    expect(explainMark(null, weights)).toEqual({ headline: '', key: [], more: [] })
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

describe('the radar chart and the sprint by sprint view', () => {
  const sc = (score) => ({ status: 'completed', score })
  const s3 = { effective_mark: 60, factors: { effort: sc(0.5), consistency: sc(0.4), requirement_fulfillment: sc(0.7), collaboration: { status: 'not_available' }, task_complexity: sc(0.6), code_ownership: { status: 'pending' } } }
  const s4 = { effective_mark: 75, factors: { effort: sc(0.8), consistency: sc(0.3), requirement_fulfillment: sc(0.9), collaboration: sc(0.5), task_complexity: sc(0.6), code_ownership: sc(0.9) } }

  it('has one spoke per factor, with the team average beside it', () => {
    const data = radarData(s4, teamAverage([s3, s4]))
    expect(data.map((d) => d.id)).toHaveLength(6)
    expect(data.find((d) => d.id === 'effort')).toMatchObject({ score: 80, average: 65, measured: true })
    expect(radarData(s3, {}).find((d) => d.id === 'code_ownership')).toMatchObject({ score: 0, measured: false })
    expect(radarData(s3, {}).find((d) => d.id === 'collaboration').average).toBeNull()
  })

  it('follows each factor from sprint to sprint, with the change since the last scored sprint', () => {
    const h = factorHistory([{ id: 'S3' }, { id: 'S4' }], (id) => (id === 'S3' ? s3 : s4))
    expect(h.enough).toBe(true)
    expect(h.marks.map((m) => m.mark)).toEqual([60, 75])
    const effort = h.rows.find((r) => r.id === 'effort')
    expect(effort.cells.map((c) => [c.score, c.delta])).toEqual([[50, null], [80, 30]])
    const collab = h.rows.find((r) => r.id === 'collaboration')
    expect(collab.cells.map((c) => [c.kind, c.score, c.delta])).toEqual([['unavailable', null, null], ['scored', 50, null]]) // nothing to compare with
  })

  it('does not follow Code Ownership sprint by sprint, and says why', () => {
    const h = factorHistory([{ id: 'S3' }, { id: 'S4' }], () => s4)
    const co = h.rows.find((r) => r.id === 'code_ownership')
    expect(co).toMatchObject({ tracked: false, cells: [] })
    expect(co.why).toContain('questions')
    expect(TRACKED.map((f) => f.id)).not.toContain('code_ownership')
  })

  it('waits for sprints that are still loading and needs two sprints to say anything', () => {
    const h = factorHistory([{ id: 'S3' }, { id: 'S4' }], (id) => (id === 'S3' ? s3 : undefined))
    expect(h.enough).toBe(false)
    expect(h.rows[0].cells[1].kind).toBe('loading')
    expect(h.marks[1].loading).toBe(true)
  })
})

describe('the agent brief and its evidence', () => {
  const result = {
    factors: { effort: { status: 'completed', score: 0.7 }, collaboration: { status: 'not_available' }, requirement_fulfillment: { status: 'completed', score: 0.5 } },
    justification: {
      summary: 'Provisional mark 61 out of 100. Strongest factor: Effort. Weakest: Consistency.',
      factors: {
        effort: { reasons: ['9 counted commits, 2335 net lines of real code, 58 files changed', '44 comment lines were not counted as work'] },
        requirement_fulfillment: { reasons: ['task MC01-304: 1 of 4 acceptance criteria met'] },
        collaboration: { reasons: ['Nobody reviewed anything in this sprint.'] },
        consistency: { reasons: [] },
      },
    },
  }

  it('lists the evidence of each factor with its kind, and leaves out a factor that has none', () => {
    const e = evidenceOf(result)
    expect(e.map((g) => g.id)).toEqual(['effort', 'requirement_fulfillment', 'collaboration'])
    expect(e[0].lines.map((l) => l.kind)).toEqual(['commit', 'code'])
    expect(e[1].lines[0]).toMatchObject({ kind: 'task' })
    expect(e[1].scored).toBe(true)
    expect(e[2].scored).toBe(false)
    expect(evidenceOf(undefined)).toEqual([])
  })

  it('gives the friendly summary, or the first two sentences of the summary', () => {
    expect(briefOf({ justification: { friendly_summary: 'A steady contributor.', summary: 'x' } })).toBe('A steady contributor.')
    expect(briefOf(result)).toBe('Provisional mark 61 out of 100. Strongest factor: Effort.')
    expect(briefOf({})).toBe('')
  })
})

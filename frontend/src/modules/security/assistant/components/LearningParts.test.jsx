import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import bundle from '../demo/demoBundle.json'
import { LearningBody } from '../pages/LearningPage.jsx'
import { AttemptThread, LearningItem, LearningSummaryCard, MockNotice, ScoreBar } from './LearningParts.jsx'
import { conceptRows, decisionLabel, decisionTone, learningSummary, scorePercent } from '../lib/format.js'

const FULL = 'sample-python-demo'
const NO_LLM = 'sample-python-no-llm'
const html = (element) => renderToStaticMarkup(<MemoryRouter>{element}</MemoryRouter>)
const data = bundle.learning[FULL]
const body = (extra) => html(<LearningBody data={data} mine={false} onMineChange={() => {}} linkFor={(i) => `/f/${i.group_id}`} {...extra} />)

describe('the comprehension checks page on the sample run', () => {
  it('says in plain words that nothing here is an assessment', () => {
    const markup = body()
    expect(markup).toContain('data-slot="mock-notice"')
    expect(markup).toContain('The Tutor is a mock: no student answered anything and nothing was graded.')
    expect(markup).toContain('None of it is an assessment of anyone.')
    expect(markup).toContain('MOCK TUTOR (simulated')
  })

  it('shows a MOCK badge next to every score', () => {
    const markup = body()
    const scores = markup.match(/data-slot="score"/g).length
    const mockScores = markup.match(/MOCK score/g).length
    expect(scores).toBe(data.summary_all.attempts)
    expect(mockScores).toBe(scores)
  })

  it('shows a MOCK badge on every check and on the summary', () => {
    const markup = body()
    const items = markup.split('data-slot="learning-item"').slice(1)
    expect(items).toHaveLength(data.items.length)
    for (const item of items) expect(item.split('data-slot="attempts"')[0]).toContain('MOCK')
    expect(markup.split('data-slot="learning-summary"')[1].split('<dl')[0]).toContain('MOCK results')
  })

  it('never calls the summary or the results an assessment, a grade or a mark', () => {
    const text = body().replace(/<[^>]+>/g, ' ')
    expect(text).not.toMatch(/\b(grade of|graded as|marks?|assessment result|passed the course)\b/i)
  })

  it('shows concepts covered, closed against open, and the questions asked', () => {
    const markup = body()
    const s = data.summary_all
    for (const [key, value] of Object.entries({ concepts: s.concepts, closed: s.closed, escalated: s.escalated, open: s.open, attempts: s.attempts })) {
      expect(markup).toMatch(new RegExp(`data-stat="${key}"[^>]*><dt[^>]*>[^<]*</dt><dd[^>]*>${value}</dd>`))
    }
    expect(markup).toContain('data-slot="concept-table"')
  })

  it('shows closed and escalated checks differently, with the reason for an escalation', () => {
    const markup = body()
    expect(markup).toMatch(/data-decision="closed"/)
    expect(markup).toMatch(/data-decision="escalated"/)
    expect(markup).toContain('escalated to the lecturer')
    expect(markup).toContain('Why it was escalated: 3 attempt(s)')
  })

  it('lists every question with its hint level and the simulated score against the threshold', () => {
    const markup = body()
    expect(markup.match(/data-attempt=/g)).toHaveLength(data.summary_all.attempts)
    expect(markup).toContain('hint level 0')
    expect(markup).toContain('hint level 2')
    expect(markup).toContain('against the threshold 0.7')
    expect(markup).toContain('Threshold for &quot;understood&quot;: 0.7 (simulated)')
  })

  it('links each check to its finding', () => {
    expect(body()).toContain('href="/f/G01"')
  })

  it('narrows the page and the summary to my checks with the "mine" filter', () => {
    const mine = data.items.filter((i) => i.mine)
    const markup = body({ mine: true })
    expect(markup.match(/data-slot="learning-item"/g)).toHaveLength(mine.length)
    expect(markup).toContain('Summary: only my findings')
    expect(markup).toContain(`data-stat="attempts"`)
    expect(markup).not.toContain('data-group="G07"') // G07 has no contributor, so it is not mine
  })

  it('says when "mine" is empty because there is no contributor id, and when none of the checks are mine', () => {
    const none = { ...data, my_contributor_ids: [], items: data.items.map((i) => ({ ...i, mine: false })) }
    const markup = html(<LearningBody data={none} mine onMineChange={() => {}} linkFor={() => '/x'} />)
    expect(markup).toContain('so &quot;mine&quot; is empty')
    expect(markup).toContain('None of the comprehension checks are for your findings')
  })
})

describe('a run without comprehension checks', () => {
  it('says there are none and that this is not a pass', () => {
    const markup = html(<LearningBody data={bundle.learning[NO_LLM]} mine={false} onMineChange={() => {}} linkFor={() => '/x'} />)
    expect(markup).toContain('No comprehension checks in this run')
    expect(markup).toContain('this is not a pass')
    expect(markup).toContain('data-slot="mock-notice"')
    expect(markup).not.toContain('data-slot="learning-summary"')
  })
})

describe('the pieces', () => {
  it('draws the score against the threshold and colours a score under it differently', () => {
    const under = html(<ScoreBar score={0.59} threshold={0.7} />)
    const over = html(<ScoreBar score={0.74} threshold={0.7} />)
    expect(under).toContain('simulated score 0.59 against the threshold 0.7')
    expect(under).toContain('bg-amber-500')
    expect(over).toContain('bg-emerald-500')
    expect(under).toContain('MOCK score')
    expect(under).toContain('width:59%')
    expect(under).toContain('left:70%')
  })

  it('labels the notice with the Tutor label only when there is one', () => {
    expect(html(<MockNotice tutor={{ label: null }} />)).not.toContain('MOCK TUTOR')
    expect(html(<MockNotice tutor={{ label: 'MOCK TUTOR (simulated)' }} />)).toContain('MOCK TUTOR (simulated)')
  })

  it('renders an item with its attempts and the escalation reason', () => {
    const item = data.items.find((i) => i.decision === 'escalated')
    const markup = html(<LearningItem item={item} threshold={0.7} to="/f" />)
    expect(markup).toContain('escalated to the lecturer')
    expect(markup).toContain(item.escalation_reason.slice(0, 20))
    expect(html(<AttemptThread attempts={item.attempts} threshold={0.7} />).match(/data-attempt=/g)).toHaveLength(item.attempts.length)
  })

  it('shows no summary table for an empty list', () => {
    expect(html(<LearningSummaryCard items={[]} scope="x" />)).not.toContain('data-slot="concept-table"')
  })
})

describe('the helpers', () => {
  it('summarises the way the Core API does', () => {
    expect(learningSummary(data.items)).toEqual({ concepts: data.summary_all.concepts, closed: data.summary_all.closed, escalated: data.summary_all.escalated, open: data.summary_all.open, attempts: data.summary_all.attempts })
    expect(learningSummary(undefined)).toEqual({ concepts: 0, closed: 0, escalated: 0, open: 0, attempts: 0 })
    expect(learningSummary([{ decision: 'skipped', attempts: [], concept_id: null }]).open).toBe(1)
  })

  it('groups the checks by concept', () => {
    const rows = conceptRows([
      { concept_id: 'a', concept: 'B concept', decision: 'closed', attempts: [1, 2] },
      { concept_id: 'a', concept: 'B concept', decision: 'escalated', attempts: [1] },
      { concept_id: 'c', concept: 'A concept', decision: 'open', attempts: [] },
    ])
    expect(rows.map((r) => r.concept)).toEqual(['A concept', 'B concept'])
    expect(rows[1]).toMatchObject({ checks: 2, closed: 1, escalated: 1, open: 0, attempts: 3 })
    expect(rows[0].open).toBe(1)
  })

  it('words decisions and clamps scores', () => {
    expect(decisionLabel('escalated')).toBe('escalated to the lecturer')
    expect(decisionLabel('whatever')).toBe('open')
    expect(decisionTone('closed')).toBe('success')
    expect(decisionTone('escalated')).toBe('warning')
    expect(decisionTone('open')).toBe('neutral')
    expect([scorePercent(0.59), scorePercent(2), scorePercent(-1), scorePercent(undefined), scorePercent('x')]).toEqual([59, 100, 0, 0, 0])
  })
})

describe('privacy on this page', () => {
  it('shows no e-mail address, local path, secret or name', () => {
    const markup = body() + body({ mine: true })
    expect(markup).not.toMatch(/[\w.+-]+@[\w-]+\.[a-z]{2,}/i)
    expect(markup).not.toMatch(/[A-Z]:\\|\/Users\/|AKIA[0-9A-Z]{16}/)
    expect(markup).not.toMatch(/Jane|Eric/)
  })
})

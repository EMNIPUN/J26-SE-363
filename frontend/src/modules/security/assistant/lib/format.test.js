import { describe, expect, it } from 'vitest'
import {
  categoryState,
  checkoutLabel,
  coverageTone,
  formatWhen,
  headline,
  llmFacts,
  problemRuns,
  scanTypeLabel,
  shortSha,
  stageTone,
  statusTone,
  toolStatusLabel,
  toolTone,
  totalOf,
  triggerLabel,
} from './format.js'

describe('tones', () => {
  it('shows a failed or skipped stage differently from a completed one', () => {
    expect(stageTone('completed')).toBe('success')
    expect(stageTone('failed')).toBe('danger')
    expect(stageTone('skipped')).toBe('warning')
    expect(stageTone('partial')).toBe('warning')
    expect(stageTone('skipped')).not.toBe(stageTone('completed'))
    expect(stageTone('failed')).not.toBe(stageTone('completed'))
  })

  it('shows tool runs that failed, timed out or were unavailable as problems, and a tool with nothing to scan as neutral', () => {
    expect(toolTone('succeeded')).toBe('success')
    expect(toolTone('failed')).toBe('danger')
    expect(toolTone('timed_out')).toBe('danger')
    expect(toolTone('unavailable')).toBe('warning')
    expect(toolTone('not_applicable')).toBe('neutral')
    expect(toolStatusLabel('timed_out')).toBe('timed out')
    expect(toolStatusLabel('something new')).toBe('something new')
  })

  it('colours coverage and verdicts', () => {
    expect(['FULL', 'REDUCED', 'NONE', 'NOTHING TO SCAN'].map(coverageTone)).toEqual(['success', 'warning', 'danger', 'neutral'])
    expect(['confirmed', 'dismissed', 'uncertain', 'not interpreted'].map(statusTone)).toEqual(['danger', 'neutral', 'warning', 'warning'])
  })
})

describe('categoryState', () => {
  const none = { confirmed: 0, dismissed: 0, uncertain: 0, 'not interpreted': 0 }

  it('says "0 findings means nothing" when the category was not covered', () => {
    const state = categoryState({ level: 'NONE' }, none)
    expect(state.tone).toBe('danger')
    expect(state.text).toMatch(/0 findings here means nothing/)
  })

  it('does not call a reduced category clean', () => {
    expect(categoryState({ level: 'REDUCED' }, none).text).toMatch(/does not mean clean/)
  })

  it('calls a category clean only with full coverage', () => {
    const state = categoryState({ level: 'FULL' }, none)
    expect(state).toEqual({ tone: 'success', text: 'Full coverage and no findings.' })
  })

  it('counts findings and treats a missing coverage entry as not covered', () => {
    expect(categoryState({ level: 'FULL' }, { ...none, confirmed: 1 }).text).toBe('1 finding reported.')
    expect(categoryState({ level: 'FULL' }, { ...none, confirmed: 2, dismissed: 1 }).text).toBe('3 findings reported.')
    expect(categoryState(undefined, none).tone).toBe('danger')
    expect(categoryState({ level: 'NOTHING TO SCAN' }, none).tone).toBe('neutral')
  })
})

describe('run facts', () => {
  it('lists only the tool runs that did not do their job', () => {
    const runs = [{ status: 'succeeded' }, { status: 'not_applicable' }, { status: 'failed' }, { status: 'unavailable' }, { status: 'timed_out' }]
    expect(problemRuns(runs).map((r) => r.status)).toEqual(['failed', 'unavailable', 'timed_out'])
    expect(problemRuns(undefined)).toEqual([])
  })

  it('says COMPLETE or INCOMPLETE', () => {
    expect(headline({ complete: true })).toBe('COMPLETE')
    expect(headline({ complete: false })).toBe('INCOMPLETE')
    expect(headline(undefined)).toBe('INCOMPLETE')
  })

  it('totals a row of counts', () => {
    expect(totalOf({ confirmed: 2, dismissed: 1, uncertain: 0 })).toBe(3)
    expect(totalOf(undefined)).toBe(0)
  })

  it('words the provenance without inventing what was not recorded', () => {
    expect(triggerLabel('manual')).toBe('Manual')
    expect(triggerLabel(undefined)).toBe('Not recorded')
    expect(scanTypeLabel('reused-scan')).toMatch(/nothing scanned now/)
    expect(checkoutLabel({ kind: 'clone-tempdir' })).toMatch(/deleted when the run ended/)
    expect(checkoutLabel({ kind: 'unknown' })).toBe('Not recorded by this run')
    expect(checkoutLabel(null)).toBe('Not recorded by this run')
    expect(shortSha('a'.repeat(40))).toBe('aaaaaaa')
    expect(shortSha(null)).toBeNull()
  })

  it('formats a UTC time and shows anything else as it is', () => {
    expect(formatWhen('2026-10-21T09:30:00Z')).toBe('21 Oct 2026, 09:30 UTC')
    expect(formatWhen('yesterday')).toBe('yesterday')
    expect(formatWhen(undefined)).toBe('Not recorded')
  })

  it('lists the model facts and says so when there is no model', () => {
    const facts = Object.fromEntries(llmFacts({ model: null, temperature: 0, seed: 7 }))
    expect(facts.Model).toMatch(/none/)
    expect(facts.Temperature).toBe(0)
    expect(facts.Seed).toBe(7)
    expect(facts['Link prompt']).toBe('not recorded')
    expect(llmFacts(undefined)).toEqual([])
  })
})

describe('findings helpers', () => {
  const f = (over) => ({ group_id: 'G', category: 'V2', status: 'confirmed', mine: false, ...over })

  it('opens the newest complete run, else the newest run', async () => {
    const { defaultRunId } = await import('./format.js')
    expect(defaultRunId([{ run_id: 'new-incomplete', complete: false }, { run_id: 'old-complete', complete: true }, { run_id: 'older', complete: true }])).toBe('old-complete')
    expect(defaultRunId([{ run_id: 'a', complete: false }, { run_id: 'b', complete: false }])).toBe('a')
    expect(defaultRunId([])).toBeNull()
    expect(defaultRunId(undefined)).toBeNull()
  })

  it('filters by type, status and mine', async () => {
    const { filterFindings } = await import('./format.js')
    const list = [f({ group_id: 'A' }), f({ group_id: 'B', status: 'dismissed', mine: true }), f({ group_id: 'C', category: 'V4', mine: true })]
    expect(filterFindings(list, { category: 'V2' }).map((x) => x.group_id)).toEqual(['A', 'B'])
    expect(filterFindings(list, { category: 'V2', status: 'dismissed' }).map((x) => x.group_id)).toEqual(['B'])
    expect(filterFindings(list, { mine: true }).map((x) => x.group_id)).toEqual(['B', 'C'])
    expect(filterFindings(undefined, {})).toEqual([])
  })

  it('counts findings by type and status, putting unknown statuses under uncertain', async () => {
    const { countByCategory } = await import('./format.js')
    const c = countByCategory([f(), f({ status: 'weird' }), f({ category: 'V5', status: 'not interpreted' })])
    expect(c.V2).toEqual({ confirmed: 1, dismissed: 0, uncertain: 1, 'not interpreted': 0 })
    expect(c.V5['not interpreted']).toBe(1)
    expect(Object.keys(c)).toEqual(['V1', 'V2', 'V3', 'V4', 'V5'])
  })

  it('picks the first type that has findings', async () => {
    const { firstCategoryWithFindings } = await import('./format.js')
    expect(firstCategoryWithFindings({ V1: { confirmed: 0 }, V3: { confirmed: 2 } })).toBe('V3')
    expect(firstCategoryWithFindings({})).toBe('V1')
  })

  it('words places, references, risk totals and the review request without code or names', async () => {
    const m = await import('./format.js')
    expect(m.whereLabel({ file_path: 'a.py', line: 3 })).toBe('a.py:3')
    expect(m.whereLabel({ file_path: 'a.py' })).toBe('a.py')
    expect(m.whereLabel({ package: 'lodash' })).toBe('lodash')
    expect(m.whereLabel({})).toBe('not located')
    expect(m.referenceLabel('https://cwe.mitre.org/data/definitions/89.html')).toBe('CWE-89')
    expect(m.referenceLabel('https://cheatsheetseries.owasp.org/cheatsheets/X.html')).toBe('OWASP Cheat Sheet')
    expect(m.referenceLabel('https://example.org/x')).toBe('example.org')
    expect(m.riskTotal([{ contribution: 24 }, { contribution: 15.5 }, { contribution: 0.1 }])).toBe(39.6)
    expect(m.riskTotal(undefined)).toBe(0)
    const text = m.reviewRequestText({ team: 'T', run: 'R', finding: { group_id: 'G1', category: 'V2', rule_id: 'r', tool: 't', file_path: 'a.py', line: 2, status: 'confirmed', snippet: 'SECRET CODE' } })
    expect(text).toContain('G1')
    expect(text).toContain('a.py:2')
    expect(text).not.toContain('SECRET CODE')
    expect(m.probeSummary(null)).toMatch(/No probe/)
    expect(m.probeSummary({ attempts: 0, decision: 'skipped' })).toBe('Not asked (skipped).')
    expect(m.probeSummary({ attempts: 2, decision: 'closed' })).toBe('closed after 2 questions')
    expect(m.linkTone('verified')).toBe('success')
    expect(m.linkTone('candidate')).toBe('warning')
  })
})

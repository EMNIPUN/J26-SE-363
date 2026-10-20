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

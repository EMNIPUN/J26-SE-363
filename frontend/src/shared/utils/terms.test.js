import { describe, expect, it } from 'vitest'
import { termOptions } from './terms.js'

const TERMS = ['2026-S2', '2026-S1', '2025-S2']

describe('termOptions', () => {
  it('lists every term when nothing is typed, and offers nothing to add', () => {
    expect(termOptions(TERMS, '').map((row) => row.kind)).toEqual(['term', 'term', 'term'])
    expect(termOptions(TERMS, '   ')).toHaveLength(3)
  })

  it('filters as you type, ignoring case', () => {
    expect(termOptions(TERMS, '2025').map((row) => row.term)).toEqual(['2025-S2', '2025'])
    expect(termOptions(TERMS, 's1').filter((row) => row.kind === 'term').map((row) => row.term)).toEqual(['2026-S1'])
  })

  it('offers "add new" for text that is not a term, last', () => {
    const rows = termOptions(TERMS, '2027-S1')
    expect(rows).toEqual([{ kind: 'new', term: '2027-S1' }])
  })

  it('does not offer to add a term that exists, whatever the case', () => {
    expect(termOptions(TERMS, '2026-s1')).toEqual([{ kind: 'term', term: '2026-S1' }])
  })

  it('trims what is typed', () => {
    expect(termOptions(TERMS, '  2027-S1 ')).toEqual([{ kind: 'new', term: '2027-S1' }])
  })

  it('does not offer a name the Core API would refuse as too long', () => {
    expect(termOptions(TERMS, 'x'.repeat(33))).toEqual([])
  })
})

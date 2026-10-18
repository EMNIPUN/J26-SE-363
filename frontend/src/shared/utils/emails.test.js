import { describe, expect, it } from 'vitest'
import { isEmail, isGithubUsername, parseEmails } from './emails.js'

describe('parseEmails', () => {
  it('splits on lines, commas, semicolons and spaces', () => {
    const { valid, invalid } = parseEmails('a@x.com, b@x.com;c@x.com\nd@x.com e@x.com')
    expect(valid).toEqual(['a@x.com', 'b@x.com', 'c@x.com', 'd@x.com', 'e@x.com'])
    expect(invalid).toEqual([])
  })

  it('lower-cases and lists each address once', () => {
    expect(parseEmails('Ada@X.com\nada@x.com').valid).toEqual(['ada@x.com'])
  })

  it('returns what is not an address instead of dropping it', () => {
    const { valid, invalid } = parseEmails('ada@x.com, not-an-email, @x.com, a@b')
    expect(valid).toEqual(['ada@x.com'])
    expect(invalid).toEqual(['not-an-email', '@x.com', 'a@b'])
  })

  it('ignores blank input', () => {
    expect(parseEmails('  \n ,; ')).toEqual({ valid: [], invalid: [] })
  })
})

describe('isEmail', () => {
  it.each(['a@b.co', 'first.last@sub.example.org'])('accepts %s', (value) => {
    expect(isEmail(value)).toBe(true)
  })

  it.each(['', 'a', 'a@b', 'a b@c.com', '@c.com'])('rejects %j', (value) => {
    expect(isEmail(value)).toBe(false)
  })
})

describe('isGithubUsername', () => {
  it.each(['sam', 'Sam-Silva', 'a1', 'x'.repeat(39)])('accepts %s', (value) => {
    expect(isGithubUsername(value)).toBe(true)
  })

  it.each(['', '-sam', 'sam-', 'sa--m', 'has space', 'x'.repeat(40), 'sam_silva'])(
    'rejects %j',
    (value) => {
      expect(isGithubUsername(value)).toBe(false)
    },
  )
})
